"""`EFF-002`/`EFF-003`: the two-phase effect ledger, proven against a
synthetic effector with a real, observable side-effect counter -- the same
`SimpleNamespace(MANIFEST=..., execute=...)` idiom
`TestRegistryEff001RegistrationGate` already established, matching
`EFF-002`'s own written acceptance criterion ("for a test effector").
`GitStateBackend`'s live counterpart is proven separately,
`@pytest.mark.live` (`tests/integration/test_effect_ledger_live.py`)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from readme_agent.capabilities import registry
from readme_agent.capabilities.effect_ledger import (
    dispatch_gated_effect,
    idempotency_key,
    retry_is_safe,
)
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.schema import RunStateV1

ORG_REPO = "acme/widget"


class _Counter:
    def __init__(self):
        self.applied = 0


class FakeStateBackend:
    def __init__(self):
        self._states: dict[str, RunStateV1] = {}
        self._locks: dict[str, tuple[str, datetime]] = {}

    def load(self, org_repo):
        return self._states.get(org_repo)

    def save(self, org_repo, state, expected_version):
        current = self._states.get(org_repo)
        cv = current.state_version if current else None
        if expected_version != cv:
            return SaveResult(outcome="stale", new_version=cv)
        nv = (cv or 0) + 1
        self._states[org_repo] = state.model_copy(update={"state_version": nv})
        return SaveResult(outcome="saved", new_version=nv)

    def acquire_lock(self, org_repo):
        existing = self._locks.get(org_repo)
        if existing is not None and existing[1] > datetime.now(UTC):
            return None
        leased_until = datetime.now(UTC) + timedelta(seconds=900)
        self._locks[org_repo] = ("holder", leased_until)
        return Lock(org_repo=org_repo, holder_id="holder", leased_until=leased_until.isoformat())

    def release_lock(self, lock):
        # Compare-and-pop by holder_id, mirroring GitStateBackend's real
        # --force-with-lease CAS-delete: only ever removes the lock THIS
        # holder created, never a since-reclaimed intruder's.
        current = self._locks.get(lock.org_repo)
        if current is not None and current[0] == lock.holder_id:
            self._locks.pop(lock.org_repo, None)

    def lock_still_held(self, lock):
        current = self._locks.get(lock.org_repo)
        return current is not None and current[0] == lock.holder_id

    def force_reclaim_lock(self, org_repo, new_holder_id="intruder"):
        """Test-only helper simulating a second runner reclaiming this
        org_repo's lease (e.g. because the first runner's lease genuinely
        expired) -- overwrites the tracked holder without going through
        `acquire_lock()`'s own expiry check, so a test can force the exact
        window `lock_still_held()` exists to detect."""
        leased_until = datetime.now(UTC) + timedelta(seconds=900)
        self._locks[org_repo] = (new_holder_id, leased_until)


def _effector_manifest(**overrides) -> CapabilityManifest:
    defaults = dict(
        capability_id="mutate_thing",
        version="1",
        name="Mutate thing",
        purpose="test effector",
        category="test",
        owner="tests",
        execution_type="gated_effector",
        side_effect_class="local_write",
        required_inputs={"org_repo": "string"},
        idempotency_inputs=["org_repo"],
        retry_policy="idempotent_only",
        # Wave 7b: the real domains.KNOWN_DOMAINS now has 2 entries, so the
        # fail-closed sunset (decision #33) requires a scoped domain for any
        # mutating manifest -- this test module isn't testing domain
        # scoping itself (test_capabilities.py's TestRegistryDomainEnforcement
        # does), so it just picks a real, already-known domain to satisfy
        # the gate without changing what's actually under test here.
        allowed_domains=["readme_reconciliation"],
    )
    return CapabilityManifest(**{**defaults, **overrides})


def _register(
    monkeypatch, manifest: CapabilityManifest, execute, reconciliation_check=None, precheck=None
):
    kwargs = {"MANIFEST": manifest, "execute": execute}
    if reconciliation_check is not None:
        kwargs["reconciliation_check"] = reconciliation_check
    if precheck is not None:
        kwargs["precheck"] = precheck
    module = SimpleNamespace(**kwargs)
    manifests, executors, reconciliation_checks, prechecks = registry._build((module,))
    monkeypatch.setattr(registry, "_MANIFESTS", manifests)
    monkeypatch.setattr(registry, "_EXECUTORS", executors)
    monkeypatch.setattr(registry, "_RECONCILIATION_CHECKS", reconciliation_checks)
    monkeypatch.setattr(registry, "_PRECHECKS", prechecks)


def _tool_call(capability_id: str, arguments: dict) -> dict:
    import json

    return {"function": {"name": capability_id, "arguments": json.dumps(arguments)}}


class TestIdempotencyKey:
    def test_same_inputs_same_key(self):
        k1 = idempotency_key("cap", {"org_repo": "a/b", "extra": 1}, ["org_repo"])
        k2 = idempotency_key("cap", {"org_repo": "a/b", "extra": 2}, ["org_repo"])
        assert k1 == k2  # "extra" is not in idempotency_inputs -- excluded from the key

    def test_different_selected_inputs_different_key(self):
        k1 = idempotency_key("cap", {"org_repo": "a/b"}, ["org_repo"])
        k2 = idempotency_key("cap", {"org_repo": "a/c"}, ["org_repo"])
        assert k1 != k2


class TestRetryIsSafe:
    def test_read_only_always_safe(self):
        m = _effector_manifest(
            side_effect_class="read_only_local", idempotency_inputs=[], retry_policy=None
        )
        assert retry_is_safe(m)

    def test_mutating_without_idempotent_only_is_unsafe(self):
        m = _effector_manifest(retry_policy=None, idempotency_inputs=["org_repo"])
        # Bypass the registration gate directly to test the function in isolation.
        assert retry_is_safe(m) is False

    def test_mutating_with_idempotent_only_is_safe(self):
        m = _effector_manifest(retry_policy="idempotent_only")
        assert retry_is_safe(m)


class TestDispatchGatedEffectHappyPath:
    def test_pending_then_applied(self, monkeypatch):
        counter = _Counter()

        def execute(org_repo):
            counter.applied += 1
            return {"applied": True, "count": counter.applied}

        _register(monkeypatch, _effector_manifest(), execute)
        backend = FakeStateBackend()

        result = dispatch_gated_effect(
            _tool_call("mutate_thing", {"org_repo": ORG_REPO}),
            {"local_write"},
            backend,
            ORG_REPO,
            caller_domain="readme_reconciliation",
        )
        assert result.outcome == "dispatched"
        assert result.dispatch.outcome == "executed"
        assert counter.applied == 1

        state = backend.load(ORG_REPO)
        assert len(state.capability_outputs) == 1
        assert state.capability_outputs[0].status == "applied"

    def test_second_dispatch_with_same_key_is_already_applied_no_reexecution(self, monkeypatch):
        counter = _Counter()

        def execute(org_repo):
            counter.applied += 1
            return {"count": counter.applied}

        _register(monkeypatch, _effector_manifest(), execute)
        backend = FakeStateBackend()
        tool_call = _tool_call("mutate_thing", {"org_repo": ORG_REPO})

        dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )
        second = dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )

        assert second.outcome == "already_applied"
        assert counter.applied == 1  # NOT re-executed -- this is the actual EFF-002 guarantee


class TestDispatchGatedEffectCrashRecovery:
    def test_deterministic_interruption_between_pending_and_applied_is_not_reexecuted(
        self, monkeypatch
    ):
        """The actual EFF-002 proof: a crash *after* the executor's side
        effect but *before* the ledger can flip the record to `applied`
        must not be silently re-applied on the next attempt. Interruption is
        deterministically triggered (the effector raises after incrementing
        its own counter), not a wall-clock race."""
        counter = _Counter()

        def crashing_execute(org_repo):
            counter.applied += 1
            raise RuntimeError("simulated crash after the real side effect landed")

        _register(monkeypatch, _effector_manifest(), crashing_execute)
        backend = FakeStateBackend()
        tool_call = _tool_call("mutate_thing", {"org_repo": ORG_REPO})

        first = dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )
        assert first.outcome == "dispatched"
        assert first.dispatch.outcome == "execution_error"
        assert counter.applied == 1

        state = backend.load(ORG_REPO)
        assert state.capability_outputs[0].status == "pending"  # never flipped to applied

        second = dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )
        assert second.outcome == "blocked_pending_reconciliation"
        assert counter.applied == 1  # NOT re-executed -- refused to guess


class TestDispatchGatedEffectLockRevalidation:
    """Decision #46/#48 (`EFF-005`, Phase 13 §13.1's F4 finding): a slow
    effector can outlive the lock's lease, letting a second runner reclaim
    it before the first runner's own terminal applied-write lands. The fix
    cannot prevent the double-dispatch itself (the effector already ran by
    the time this is checked) -- it prevents the ledger from dishonestly
    recording the first runner's work as independently `applied` once it
    can no longer prove it was still the exclusive holder."""

    def test_lock_reclaimed_during_effector_leaves_record_pending_not_applied(self, monkeypatch):
        counter = _Counter()
        backend = FakeStateBackend()

        def slow_execute(org_repo):
            counter.applied += 1
            # Simulate the effector outliving its lease: a second runner's
            # acquire_lock() legitimately reclaims org_repo's lock while
            # this effector is still "running".
            backend.force_reclaim_lock(org_repo)
            return {"done": True}

        _register(monkeypatch, _effector_manifest(), slow_execute)
        tool_call = _tool_call("mutate_thing", {"org_repo": ORG_REPO})

        result = dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )

        assert result.outcome == "dispatched"
        assert result.dispatch.outcome == "executed"  # the real side effect DID happen
        assert counter.applied == 1
        assert result.detail is not None and "reclaimed" in result.detail

        state = backend.load(ORG_REPO)
        assert state.capability_outputs[0].status == "pending"  # NOT falsely marked applied

        # A second attempt for the identical idempotency key must not
        # silently succeed either -- whether because the intruder still
        # holds the lock, or because the record is pending with no
        # reconciliation check, either way this is never "already_applied".
        second = dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )
        assert second.outcome == "blocked_pending_reconciliation"

    def test_lock_not_reclaimed_writes_applied_as_before(self, monkeypatch):
        """Regression guard: the new check must not change behavior in the
        overwhelmingly common case where nothing reclaims the lock."""
        counter = _Counter()
        backend = FakeStateBackend()

        def fast_execute(org_repo):
            counter.applied += 1
            return {"done": True}

        _register(monkeypatch, _effector_manifest(), fast_execute)
        tool_call = _tool_call("mutate_thing", {"org_repo": ORG_REPO})

        result = dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )

        assert result.outcome == "dispatched"
        assert result.dispatch.outcome == "executed"
        assert result.detail is None
        state = backend.load(ORG_REPO)
        assert state.capability_outputs[0].status == "applied"


class TestDispatchGatedEffectRetryInertness:
    def test_a_failed_attempt_always_blocks_the_next_one_regardless_of_retry_policy(
        self, monkeypatch
    ):
        """The ledger's own `pending`-after-failure check fires for *any*
        subsequent attempt with the same key, regardless of `retry_policy`
        -- "did the effect land" is genuinely unknown here, a strictly
        stronger reason to refuse than `retry_policy` alone. `EFF-003`'s own
        enforcement point is one layer up: `supervisor/repair.py`'s
        `retry_is_safe()` gate decides whether to even *propose* dispatching
        this capability+arguments again in the first place (see
        `test_repair.py`) -- this test proves the ledger backstops that
        decision defensively even if something else tried to bypass it."""

        def failing_execute(org_repo):
            raise RuntimeError("boom")

        _register(
            monkeypatch,
            _effector_manifest(retry_policy="manual_reconciliation_required"),
            failing_execute,
        )
        backend = FakeStateBackend()
        tool_call = _tool_call("mutate_thing", {"org_repo": ORG_REPO})

        first = dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )
        assert first.dispatch.outcome == "execution_error"

        second = dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )
        assert second.outcome == "blocked_pending_reconciliation"


class TestDispatchGatedEffectReconciliationCheck:
    """Wave 7's fix for `EFF-001`'s remaining gap: a registered capability's
    `reconciliation_check` gets a chance to answer "did this already happen?"
    before a stale `pending` record is treated as an unrecoverable blocker."""

    def test_reconciliation_check_confirms_and_backfills_to_applied(self, monkeypatch):
        counter = _Counter()

        def crashing_execute(org_repo):
            counter.applied += 1
            raise RuntimeError("simulated crash after the real side effect landed")

        def reconciliation_check(arguments):
            # Simulates re-observing reality and confirming the effect did land.
            return {"reconciled": True, "org_repo": arguments["org_repo"]}

        _register(monkeypatch, _effector_manifest(), crashing_execute, reconciliation_check)
        backend = FakeStateBackend()
        tool_call = _tool_call("mutate_thing", {"org_repo": ORG_REPO})

        first = dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )
        assert first.dispatch.outcome == "execution_error"
        assert backend.load(ORG_REPO).capability_outputs[0].status == "pending"

        second = dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )
        assert second.outcome == "already_applied"
        assert second.cached_result == {"reconciled": True, "org_repo": ORG_REPO}
        assert counter.applied == 1  # still not re-executed

        # The ledger's own record was corrected, not just the return value.
        state = backend.load(ORG_REPO)
        assert state.capability_outputs[0].status == "applied"
        assert state.capability_outputs[0].result == {"reconciled": True, "org_repo": ORG_REPO}

    def test_reconciliation_check_returning_none_still_blocks(self, monkeypatch):
        def crashing_execute(org_repo):
            raise RuntimeError("boom")

        def reconciliation_check(arguments):
            return None  # cannot confirm -- stay blocked, same as no check at all

        _register(monkeypatch, _effector_manifest(), crashing_execute, reconciliation_check)
        backend = FakeStateBackend()
        tool_call = _tool_call("mutate_thing", {"org_repo": ORG_REPO})

        dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )
        second = dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )

        assert second.outcome == "blocked_pending_reconciliation"
        assert backend.load(ORG_REPO).capability_outputs[0].status == "pending"

    def test_the_real_commit_readme_write_capability_has_a_reconciliation_check_registered(self):
        """Wave 7g: `EFF-001`'s remaining gap, closed against the real
        registered mutating capability, not just a synthetic effector --
        the crash-recovery mechanism itself is exercised end to end via the
        live proof (`plans/master.md`), this confirms the wiring is real."""
        check = registry.get_reconciliation_check("commit_readme_write")
        assert check is not None


class TestPrecheck:
    """Wave 8 (`EFF-002` ordering fix, production-reliability pass): a
    rejecting `precheck()` must never write a pending ledger entry at all --
    proven by inspecting the backend's own state directly, not just the
    return value, which is exactly the distinction between "fails cheaply"
    and "poisons the ledger" the fix exists to make."""

    def test_rejecting_precheck_writes_zero_ledger_entries(self, monkeypatch):
        counter = _Counter()

        def execute(org_repo):
            counter.applied += 1
            return {"applied": True}

        def precheck(arguments):
            return "synthetic precondition failure for testing"

        _register(monkeypatch, _effector_manifest(), execute, precheck=precheck)
        backend = FakeStateBackend()

        result = dispatch_gated_effect(
            _tool_call("mutate_thing", {"org_repo": ORG_REPO}),
            {"local_write"},
            backend,
            ORG_REPO,
            caller_domain="readme_reconciliation",
        )

        assert result.outcome == "dispatched"
        assert result.dispatch.outcome == "rejected_precondition_failed"
        assert result.dispatch.error == "synthetic precondition failure for testing"
        assert counter.applied == 0  # the executor itself was never reached
        assert backend.load(ORG_REPO) is None  # zero ledger writes -- no pending entry at all

    def test_accepting_precheck_proceeds_normally(self, monkeypatch):
        counter = _Counter()

        def execute(org_repo):
            counter.applied += 1
            return {"applied": True}

        def precheck(arguments):
            return None  # accept

        _register(monkeypatch, _effector_manifest(), execute, precheck=precheck)
        backend = FakeStateBackend()

        result = dispatch_gated_effect(
            _tool_call("mutate_thing", {"org_repo": ORG_REPO}),
            {"local_write"},
            backend,
            ORG_REPO,
            caller_domain="readme_reconciliation",
        )

        assert result.outcome == "dispatched"
        assert result.dispatch.outcome == "executed"
        assert counter.applied == 1

    def test_a_repeat_dispatch_after_a_rejected_precheck_is_not_blocked(self, monkeypatch):
        """The actual proof this matters: unlike a genuine crash-mid-effect,
        a precheck rejection leaves no trace at all, so a corrected retry
        with the same idempotency-key-bearing arguments proceeds normally --
        never `blocked_pending_reconciliation`."""
        counter = _Counter()
        verdict = {"reject": True}

        def execute(org_repo):
            counter.applied += 1
            return {"applied": True}

        def precheck(arguments):
            return "rejected" if verdict["reject"] else None

        _register(monkeypatch, _effector_manifest(), execute, precheck=precheck)
        backend = FakeStateBackend()
        tool_call = _tool_call("mutate_thing", {"org_repo": ORG_REPO})

        first = dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )
        assert first.dispatch.outcome == "rejected_precondition_failed"

        verdict["reject"] = False
        second = dispatch_gated_effect(
            tool_call, {"local_write"}, backend, ORG_REPO, caller_domain="readme_reconciliation"
        )
        assert second.outcome == "dispatched"
        assert second.dispatch.outcome == "executed"
        assert counter.applied == 1


class TestDispatchGatedEffectPassthrough:
    def test_read_only_capability_bypasses_the_ledger_entirely(self):
        """A non-mutating capability_id is never gated -- plain dispatch,
        the ledger has nothing to add (matches every existing registered
        capability today)."""
        backend = FakeStateBackend()
        result = dispatch_gated_effect(
            _tool_call("inspect_repository", {"org_repo": "not-a-real-repo/x"}),
            {"read_only_local"},
            backend,
            "not-a-real-repo/x",
        )
        assert result.outcome == "dispatched"
        # Nothing written to the ledger for a read-only capability.
        assert backend.load("not-a-real-repo/x") is None
