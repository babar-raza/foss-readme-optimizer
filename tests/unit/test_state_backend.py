"""Proves the `StateBackend` Protocol's contract (`MEM-003`: "interface + at
least one real backend") against an in-memory fake -- no git, no network.
`state/git_backend.py`'s live counterpart is proven separately, `@pytest.mark.live`
(`tests/integration/test_state_git_backend_live.py`), since it needs a real push.
"""

from datetime import UTC, datetime, timedelta

import pytest

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.domain_state import save_domain
from readme_agent.state.schema import DomainStateV1, RunStateV1


class FakeStateBackend:
    """In-memory `StateBackend`. Mirrors `state/git_backend.py::GitStateBackend`'s
    CAS/lock semantics exactly (same accept/reject rules), just without git."""

    def __init__(self):
        self._states: dict[str, RunStateV1] = {}
        self._locks: dict[str, tuple[str, datetime]] = {}
        # Wave 8.5 (SCL-005 extension): a second, genuinely separate tracking
        # dict for the run-lock, mirroring GitStateBackend's own two-dict
        # design exactly -- keyed only by org_repo, so one dict cannot safely
        # hold both lock families' state simultaneously for the same repo.
        self._run_locks: dict[str, tuple[str, datetime]] = {}
        # Wave 8.6 (`OPS-011` extension): the global (not per-org_repo)
        # model-route registry, keyed by job name.
        self._model_routes: dict = {}

    def load(self, org_repo: str) -> RunStateV1 | None:
        return self._states.get(org_repo)

    def save(self, org_repo: str, state: RunStateV1, expected_version: int | None) -> SaveResult:
        current = self._states.get(org_repo)
        current_version = current.state_version if current else None
        if expected_version != current_version:
            return SaveResult(outcome="stale", new_version=current_version)
        new_version = (current_version or 0) + 1
        self._states[org_repo] = state.model_copy(
            update={"org_repo": org_repo, "state_version": new_version}
        )
        return SaveResult(outcome="saved", new_version=new_version)

    def _acquire(self, org_repo: str, tracking: dict[str, tuple[str, datetime]]) -> Lock | None:
        existing = tracking.get(org_repo)
        if existing is not None and existing[1] > datetime.now(UTC):
            return None
        leased_until = datetime.now(UTC) + timedelta(seconds=900)
        holder_id = f"fake-holder-{len(tracking)}"
        tracking[org_repo] = (holder_id, leased_until)
        return Lock(org_repo=org_repo, holder_id=holder_id, leased_until=leased_until.isoformat())

    def acquire_lock(self, org_repo: str) -> Lock | None:
        return self._acquire(org_repo, self._locks)

    def release_lock(self, lock: Lock) -> None:
        self._locks.pop(lock.org_repo, None)

    def lock_still_held(self, lock: Lock) -> bool:
        current = self._locks.get(lock.org_repo)
        return current is not None and current[0] == lock.holder_id

    def acquire_run_lock(self, org_repo: str) -> Lock | None:
        return self._acquire(org_repo, self._run_locks)

    def release_run_lock(self, lock: Lock) -> None:
        self._run_locks.pop(lock.org_repo, None)

    def load_model_route_status(self, job: str):
        return self._model_routes.get(job)

    def save_model_route_status(self, status) -> None:
        self._model_routes[status.job] = status


class TestFakeStateBackendCAS:
    def test_first_write_succeeds_with_expected_version_none(self):
        backend = FakeStateBackend()
        result = backend.save(
            "org/repo", RunStateV1(org_repo="org/repo", accepted_status="GENERATED"), None
        )
        assert result.outcome == "saved"
        assert result.new_version == 1
        loaded = backend.load("org/repo")
        assert loaded is not None
        assert loaded.state_version == 1

    def test_first_write_with_nonnone_expected_version_is_stale(self):
        backend = FakeStateBackend()
        result = backend.save("org/repo", RunStateV1(org_repo="org/repo"), 5)
        assert result.outcome == "stale"

    def test_matching_expected_version_accepts_and_increments(self):
        backend = FakeStateBackend()
        backend.save("org/repo", RunStateV1(org_repo="org/repo"), None)
        result = backend.save(
            "org/repo", RunStateV1(org_repo="org/repo", accepted_status="COMPLIANT_NO_CHANGE"), 1
        )
        assert result.outcome == "saved"
        assert result.new_version == 2

    def test_stale_expected_version_rejected_and_reports_real_version(self):
        backend = FakeStateBackend()
        backend.save("org/repo", RunStateV1(org_repo="org/repo"), None)
        result = backend.save("org/repo", RunStateV1(org_repo="org/repo"), 0)
        assert result.outcome == "stale"
        assert result.new_version == 1

    def test_concurrent_writes_to_different_repos_never_conflict(self):
        """The granularity fix Wave 4's reassessment exists to prove: two
        unrelated repos' writes must never falsely conflict."""
        backend = FakeStateBackend()
        result_a = backend.save("org/a", RunStateV1(org_repo="org/a"), None)
        result_b = backend.save("org/b", RunStateV1(org_repo="org/b"), None)
        assert result_a.outcome == "saved"
        assert result_b.outcome == "saved"


class TestFakeStateBackendLock:
    def test_acquire_when_unlocked_succeeds(self):
        backend = FakeStateBackend()
        lock = backend.acquire_lock("org/repo")
        assert lock is not None
        assert lock.org_repo == "org/repo"

    def test_acquire_when_held_and_unexpired_fails(self):
        backend = FakeStateBackend()
        backend.acquire_lock("org/repo")
        assert backend.acquire_lock("org/repo") is None

    def test_acquire_reclaims_an_expired_lease(self):
        backend = FakeStateBackend()
        backend.acquire_lock("org/repo")
        backend._locks["org/repo"] = ("crashed-holder", datetime.now(UTC) - timedelta(seconds=1))
        lock = backend.acquire_lock("org/repo")
        assert lock is not None

    def test_release_then_acquire_succeeds(self):
        backend = FakeStateBackend()
        lock = backend.acquire_lock("org/repo")
        assert lock is not None
        backend.release_lock(lock)
        assert backend.acquire_lock("org/repo") is not None


class TestFakeStateBackendLockRevalidation:
    """Decision #46/#48 (`EFF-005`, Phase 13 §13.1's F4 finding): the
    holder-identity revalidation `effect_ledger.py::dispatch_gated_effect()`
    now performs immediately before its terminal `applied` write."""

    def test_still_held_by_the_same_holder_is_true(self):
        backend = FakeStateBackend()
        lock = backend.acquire_lock("org/repo")
        assert backend.lock_still_held(lock) is True

    def test_reclaimed_by_a_different_holder_is_false(self):
        backend = FakeStateBackend()
        lock = backend.acquire_lock("org/repo")
        # Simulate the lease genuinely expiring and a second runner
        # legitimately reclaiming it -- the same mechanism
        # test_acquire_reclaims_an_expired_lease already proves.
        backend._locks["org/repo"] = ("intruder", datetime.now(UTC) + timedelta(seconds=900))
        assert backend.lock_still_held(lock) is False

    def test_released_lock_is_not_still_held(self):
        backend = FakeStateBackend()
        lock = backend.acquire_lock("org/repo")
        backend.release_lock(lock)
        assert backend.lock_still_held(lock) is False


class TestFakeStateBackendRunLock:
    """Wave 8.5 (SCL-005 extension) -- mirrors TestFakeStateBackendLock's own
    four tests exactly, proving the run-lock's behavior matches the
    existing per-op lock's semantics by construction (same shared `_acquire`
    helper), not by two independently-written test suites that could
    silently diverge. Also proves the two lock families are genuinely
    independent -- acquiring one never affects the other for the same repo."""

    def test_acquire_when_unlocked_succeeds(self):
        backend = FakeStateBackend()
        lock = backend.acquire_run_lock("org/repo")
        assert lock is not None
        assert lock.org_repo == "org/repo"

    def test_acquire_when_held_and_unexpired_fails(self):
        backend = FakeStateBackend()
        backend.acquire_run_lock("org/repo")
        assert backend.acquire_run_lock("org/repo") is None

    def test_acquire_reclaims_an_expired_lease(self):
        backend = FakeStateBackend()
        backend.acquire_run_lock("org/repo")
        backend._run_locks["org/repo"] = (
            "crashed-holder",
            datetime.now(UTC) - timedelta(seconds=1),
        )
        lock = backend.acquire_run_lock("org/repo")
        assert lock is not None

    def test_release_then_acquire_succeeds(self):
        backend = FakeStateBackend()
        lock = backend.acquire_run_lock("org/repo")
        assert lock is not None
        backend.release_run_lock(lock)
        assert backend.acquire_run_lock("org/repo") is not None

    def test_run_lock_and_op_lock_are_genuinely_independent(self):
        """The exact property the new run-lock's real-ref-difference relies
        on: holding one lock family for a repo must never block the other."""
        backend = FakeStateBackend()
        op_lock = backend.acquire_lock("org/repo")
        assert op_lock is not None
        run_lock = backend.acquire_run_lock("org/repo")
        assert run_lock is not None  # not blocked by the held op lock
        assert backend.acquire_lock("org/repo") is None  # op lock still genuinely held
        assert backend.acquire_run_lock("org/repo") is None  # run lock still genuinely held


class TestSafeReleaseLock:
    """Found live, 2026-07-22: every `finally: backend.release_lock(lock)`
    in this codebase (`domain_state.py` x3, `effect_ledger.py`,
    `supervisor/loop.py` x2) let a genuine release failure raise straight out
    of a `finally:` block, discarding whatever the `try` block was already
    returning/raising. `safe_release_lock()` is the one shared fix all six
    call sites now use."""

    def test_successful_release_is_silent(self, capsys):
        from readme_agent.state.backend import safe_release_lock

        backend = FakeStateBackend()
        lock = backend.acquire_lock("org/repo")

        safe_release_lock(backend.release_lock, lock, label="lock")

        assert backend.acquire_lock("org/repo") is not None  # actually released
        assert capsys.readouterr().err == ""

    def test_release_failure_is_caught_and_logged_not_raised(self, capsys):
        from readme_agent.state.backend import safe_release_lock

        backend = FakeStateBackend()
        lock = backend.acquire_lock("org/repo")

        def _raising_release(lock):
            raise RuntimeError("push failed: connection reset")

        safe_release_lock(_raising_release, lock, label="lock")  # must not raise

        err = capsys.readouterr().err
        assert "warning: releasing lock" in err
        assert "org/repo" in err
        assert "connection reset" in err


class TestSaveDomain:
    """MEM-004/Decision #34 -- the concrete regression test for root cause
    #2 (RunStateV1's flat accepted_* fields silently colliding/clobbering
    once more than one specialist writes into the same org_repo record)."""

    def test_first_domain_write_creates_the_record(self):
        backend = FakeStateBackend()
        result = save_domain(
            backend,
            "org/repo",
            "readme",
            DomainStateV1(domain="readme", accepted_status="GENERATED"),
        )
        assert result.outcome == "saved"
        loaded = backend.load("org/repo")
        assert loaded.domain_states["readme"].accepted_status == "GENERATED"

    def test_two_different_domains_both_land_without_collision(self):
        backend = FakeStateBackend()
        save_domain(
            backend,
            "org/repo",
            "readme",
            DomainStateV1(domain="readme", accepted_status="GENERATED"),
        )
        save_domain(
            backend,
            "org/repo",
            "metadata",
            DomainStateV1(domain="metadata", accepted_status="COMPLIANT_NO_CHANGE"),
        )
        loaded = backend.load("org/repo")
        assert loaded.domain_states["readme"].accepted_status == "GENERATED"
        assert loaded.domain_states["metadata"].accepted_status == "COMPLIANT_NO_CHANGE"

    def test_a_domain_write_never_clobbers_another_domains_already_accepted_result(self):
        """The exact false-positive-clobber scenario from the investigation
        doc: writing metadata's result must not erase readme's, even though
        both target the same org_repo record and the same state_version
        counter."""
        backend = FakeStateBackend()
        save_domain(
            backend,
            "org/repo",
            "readme",
            DomainStateV1(domain="readme", accepted_status="GENERATED"),
        )
        save_domain(
            backend,
            "org/repo",
            "metadata",
            DomainStateV1(domain="metadata", accepted_status="COMPLIANT_NO_CHANGE"),
        )
        save_domain(
            backend,
            "org/repo",
            "readme",
            DomainStateV1(domain="readme", accepted_status="COMPLIANT_NO_CHANGE"),
        )
        loaded = backend.load("org/repo")
        assert loaded.domain_states["readme"].accepted_status == "COMPLIANT_NO_CHANGE"
        assert loaded.domain_states["metadata"].accepted_status == "COMPLIANT_NO_CHANGE"

    def test_details_payload_survives_a_cas_retry_cycle_unchanged(self):
        """Wave 7: `DomainStateV1.details`'s round-trip through the exact
        write path every specialist uses, not just plain JSON serialization
        (already covered in test_state_schema.py)."""
        backend = FakeStateBackend()
        payload = {"proposed_topics": ["pdf", "java"], "current_description": "A PDF library"}
        save_domain(
            backend,
            "org/repo",
            "metadata_presentation",
            DomainStateV1(
                domain="metadata_presentation", accepted_status="PROPOSED", details=payload
            ),
        )
        # A second, unrelated domain's write forces a real reload -- proves
        # `details` isn't silently dropped by the "patch only my own key on
        # a freshly reloaded copy" mechanics `save_domain()` relies on.
        save_domain(
            backend,
            "org/repo",
            "readme",
            DomainStateV1(domain="readme", accepted_status="GENERATED"),
        )
        loaded = backend.load("org/repo")
        assert loaded.domain_states["metadata_presentation"].details == payload

    def test_stale_retry_carries_forward_a_concurrent_writers_result(self):
        """Simulates the lease-expiry edge case: another writer's save lands
        between this caller's load and save. The bounded retry must reload
        and merge rather than either failing outright or clobbering the
        concurrent writer's result."""
        backend = FakeStateBackend()
        save_domain(
            backend,
            "org/repo",
            "readme",
            DomainStateV1(domain="readme", accepted_status="GENERATED"),
        )

        real_save = backend.save
        calls = {"n": 0}

        def flaky_save(org_repo, state, expected_version):
            calls["n"] += 1
            if calls["n"] == 1:
                # A concurrent writer's save lands first, out from under
                # this caller's stale expected_version -- it merges onto
                # the real current state (readme already present), exactly
                # as a proper concurrent save_domain() call would.
                concurrent_base = backend.load(org_repo)
                concurrent_state = concurrent_base.model_copy(
                    update={
                        "domain_states": {
                            **concurrent_base.domain_states,
                            "metadata": DomainStateV1(
                                domain="metadata", accepted_status="GENERATED"
                            ),
                        }
                    }
                )
                real_save(org_repo, concurrent_state, expected_version)
                return SaveResult(outcome="stale", new_version=None)
            return real_save(org_repo, state, expected_version)

        backend.save = flaky_save

        result = save_domain(
            backend,
            "org/repo",
            "visuals",
            DomainStateV1(domain="visuals", accepted_status="GENERATED"),
        )

        assert result.outcome == "saved"
        loaded = backend.load("org/repo")
        assert set(loaded.domain_states) == {"readme", "metadata", "visuals"}

    def test_raises_after_exhausting_retries_on_persistent_staleness(self):
        backend = FakeStateBackend()

        def always_stale(org_repo, state, expected_version):
            return SaveResult(outcome="stale", new_version=99)

        backend.save = always_stale

        with pytest.raises(StateBackendError):
            save_domain(
                backend,
                "org/repo",
                "readme",
                DomainStateV1(domain="readme", accepted_status="GENERATED"),
                max_retries=2,
            )

    def test_raises_when_lock_cannot_be_acquired(self):
        backend = FakeStateBackend()
        held = backend.acquire_lock("org/repo")
        assert held is not None

        with pytest.raises(StateBackendError):
            save_domain(
                backend,
                "org/repo",
                "readme",
                DomainStateV1(domain="readme", accepted_status="GENERATED"),
            )

    def test_releases_the_lock_even_when_save_raises(self):
        backend = FakeStateBackend()

        def boom(org_repo, state, expected_version):
            raise RuntimeError("network exploded")

        backend.save = boom

        with pytest.raises(RuntimeError):
            save_domain(
                backend,
                "org/repo",
                "readme",
                DomainStateV1(domain="readme", accepted_status="GENERATED"),
            )

        # Lock must have been released despite the exception -- otherwise a
        # single failed write would permanently wedge the repo for
        # LOCK_LEASE_SECONDS.
        assert backend.acquire_lock("org/repo") is not None


class TestFakeStateBackendModelRoute:
    """Wave 8.6 (`OPS-011` extension): the global (not per-org_repo)
    model-route registry."""

    def test_no_status_recorded_returns_none(self):
        backend = FakeStateBackend()
        assert backend.load_model_route_status("supervisor_planning") is None

    def test_saved_status_round_trips(self):
        from readme_agent.state.schema import ModelRouteStatusV1

        backend = FakeStateBackend()
        backend.save_model_route_status(
            ModelRouteStatusV1(job="supervisor_planning", status="disabled", reason="low pass rate")
        )
        loaded = backend.load_model_route_status("supervisor_planning")
        assert loaded is not None
        assert loaded.status == "disabled"
        assert loaded.reason == "low pass rate"

    def test_different_jobs_are_independent(self):
        from readme_agent.state.schema import ModelRouteStatusV1

        backend = FakeStateBackend()
        backend.save_model_route_status(
            ModelRouteStatusV1(job="supervisor_planning", status="disabled")
        )
        assert backend.load_model_route_status("prose_quality_check") is None

    def test_re_enabling_overwrites_the_prior_status(self):
        from readme_agent.state.schema import ModelRouteStatusV1

        backend = FakeStateBackend()
        backend.save_model_route_status(
            ModelRouteStatusV1(job="supervisor_planning", status="disabled", reason="bad")
        )
        backend.save_model_route_status(
            ModelRouteStatusV1(
                job="supervisor_planning", status="enabled", re_enabled_by="human", reason="fixed"
            )
        )
        loaded = backend.load_model_route_status("supervisor_planning")
        assert loaded.status == "enabled"
        assert loaded.re_enabled_by == "human"
