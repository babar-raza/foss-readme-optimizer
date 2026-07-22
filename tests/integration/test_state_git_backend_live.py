"""Live proof of `state/git_backend.py::GitStateBackend` -- real `git push`
against this project's own remote, never a target repo, and only ever
`refs/readme-agent-state/...` refs (the backend's own dedicated namespace,
disjoint from every branch a human would use). Every ref this file creates
is deleted in a `finally` block regardless of outcome.

Specifically proves the two things Wave 4's backend-choice reassessment
exists to guarantee (`plans/master.md` decision -- see "Backend evaluation
and choice (reassessed)"): a per-`org_repo` git ref makes cross-repo CAS
false positives structurally impossible, while same-repo CAS conflicts are
still correctly caught.

CAUTION: run only with explicit confirmation -- this pushes real commits
(and deletes them again) to whatever `origin` remote the invoking working
directory has configured. Not run as part of default `pytest -q`
(`@pytest.mark.live`, excluded by `addopts = "-m 'not live'"`).

PREREQUISITE (`OPS-009`, found 2026-07-19 -- `git push` hung silently and
indefinitely, ~35 minutes, no error, no output, before this was diagnosed):
a local (non-CI) run needs real push credentials for `origin` configured
*before* invoking this file, or `git push` blocks forever with no visible
error -- neither `run_git()`'s 120s subprocess timeout nor pytest itself
catches this, because the hang is inside git's own credential-resolution
step, not the timed operation. `GH_TOKEN` alone is not sufficient; nothing
wires it into git's auth path automatically. Fix, one-time per shell
session, removed immediately after (never leave this configured):
    AUTH=$(printf 'x-access-token:%s' "$GH_TOKEN" | base64 -w0)
    git config --local http.https://github.com/.extraheader "AUTHORIZATION: basic $AUTH"
    # ... run the live tests ...
    git config --local --unset http.https://github.com/.extraheader
GitHub Actions itself is unaffected -- `actions/checkout` wires the
runner-provided token into git's credentials automatically, which is why
`RUN-003`'s `act` reproduction never hit this.
"""

import json
import time
import uuid

import pytest

from readme_agent.gitsafety._git import run_git
from readme_agent.state import git_backend as git_backend_module
from readme_agent.state.git_backend import (
    LOCK_REF_PREFIX,
    MODEL_ROUTE_REF,
    RUN_LOCK_REF_PREFIX,
    STATE_REF_PREFIX,
    GitStateBackend,
    _fetch_remote_sha,
    _read_blob,
    _ref_key,
    _write_commit,
)
from readme_agent.state.schema import ModelRouteStatusV1, RunStateV1


def _disposable_org_repo() -> str:
    # A real slash-delimited org/repo shape, but a name no real
    # data/products.json entry will ever use -- never collides with
    # production state, identifiable as test-created if ever seen.
    return f"readme-agent-state-live-test/{uuid.uuid4().hex[:12]}"


def _delete_refs(*org_repos: str) -> None:
    for org_repo in org_repos:
        key = _ref_key(org_repo)
        run_git(["push", "origin", f":{STATE_REF_PREFIX}/{key}"])
        run_git(["push", "origin", f":{LOCK_REF_PREFIX}/{key}"])
        # Wave 8.5 (SCL-005 extension): the run-lock's own ref, cleaned up
        # the same way as the existing per-op lock ref above.
        run_git(["push", "origin", f":{RUN_LOCK_REF_PREFIX}/{key}"])


@pytest.mark.live
def test_save_then_load_round_trips_for_real():
    org_repo = _disposable_org_repo()
    backend = GitStateBackend()
    try:
        assert backend.load(org_repo) is None

        state = RunStateV1(
            org_repo=org_repo, accepted_facts_hash="abc123", accepted_status="GENERATED"
        )
        result = backend.save(org_repo, state, expected_version=None)
        assert result.outcome == "saved"
        assert result.new_version == 1

        loaded = backend.load(org_repo)
        assert loaded is not None
        assert loaded.accepted_facts_hash == "abc123"
        assert loaded.accepted_status == "GENERATED"
        assert loaded.state_version == 1
    finally:
        _delete_refs(org_repo)


@pytest.mark.live
def test_writes_to_different_repos_never_falsely_conflict():
    """The granularity fix this reassessment exists to prove: two unrelated
    repos' writes must never spuriously conflict -- the false positive a
    single shared branch (the reversed first draft) would have produced."""
    org_repo_a = _disposable_org_repo()
    org_repo_b = _disposable_org_repo()
    backend = GitStateBackend()
    try:
        result_a = backend.save(
            org_repo_a, RunStateV1(org_repo=org_repo_a, accepted_status="GENERATED"), None
        )
        result_b = backend.save(
            org_repo_b, RunStateV1(org_repo=org_repo_b, accepted_status="GENERATED"), None
        )
        assert result_a.outcome == "saved"
        assert result_b.outcome == "saved"
    finally:
        _delete_refs(org_repo_a, org_repo_b)


@pytest.mark.live
def test_two_writers_racing_the_same_repo_yield_exactly_one_saved_one_stale():
    org_repo = _disposable_org_repo()
    backend = GitStateBackend()
    try:
        first = backend.save(
            org_repo, RunStateV1(org_repo=org_repo, accepted_status="GENERATED"), None
        )
        assert first.outcome == "saved"

        # Two racers both still believe version 1 is current -- only one push
        # can win the non-fast-forward check.
        result_one = backend.save(
            org_repo, RunStateV1(org_repo=org_repo, accepted_status="COMPLIANT_NO_CHANGE"), 1
        )
        result_two = backend.save(
            org_repo, RunStateV1(org_repo=org_repo, accepted_status="COMPLIANT_NO_CHANGE"), 1
        )
        assert {result_one.outcome, result_two.outcome} == {"saved", "stale"}
    finally:
        _delete_refs(org_repo)


@pytest.mark.live
def test_lock_acquire_release_and_reclaim_after_lease_expiry(monkeypatch):
    # Real network round-trips (fetch + read + push against GitHub) took
    # several seconds each in practice -- a 1-second lease made the "held,
    # not expired" assertion below flaky (the second acquire_lock() call's
    # own round-trip could outlast a 1-second lease on its own, expiring it
    # before the check even ran). 8s comfortably exceeds one full
    # acquire_lock() round-trip observed here (~2-5s).
    LEASE_SECONDS = 8
    org_repo = _disposable_org_repo()
    backend = GitStateBackend()
    monkeypatch.setattr(git_backend_module, "LOCK_LEASE_SECONDS", LEASE_SECONDS)
    try:
        first = backend.acquire_lock(org_repo)
        assert first is not None
        assert backend.acquire_lock(org_repo) is None  # held, not expired

        backend.release_lock(first)
        second = backend.acquire_lock(org_repo)
        assert second is not None
        assert second.holder_id != first.holder_id

        time.sleep(LEASE_SECONDS + 0.5)
        reclaimed = backend.acquire_lock(org_repo)
        assert reclaimed is not None
        assert reclaimed.holder_id != second.holder_id
    finally:
        _delete_refs(org_repo)


@pytest.mark.live
def test_run_lock_acquire_release_and_reclaim_after_lease_expiry(monkeypatch):
    """Wave 8.5 (SCL-005 extension) -- mirrors
    test_lock_acquire_release_and_reclaim_after_lease_expiry exactly, proving
    the new run-lock's CAS/lease/reclaim semantics against a real remote.
    Also proves the two lock families are genuinely independent refs: the
    run-lock is acquirable even while the (separate) per-op lock is held."""
    LEASE_SECONDS = 8
    org_repo = _disposable_org_repo()
    backend = GitStateBackend()
    monkeypatch.setattr(git_backend_module, "RUN_LOCK_LEASE_SECONDS", LEASE_SECONDS)
    try:
        op_lock = backend.acquire_lock(org_repo)
        assert op_lock is not None

        first = backend.acquire_run_lock(org_repo)
        assert first is not None  # not blocked by the held, separate per-op lock
        assert backend.acquire_run_lock(org_repo) is None  # held, not expired

        backend.release_run_lock(first)
        second = backend.acquire_run_lock(org_repo)
        assert second is not None
        assert second.holder_id != first.holder_id

        time.sleep(LEASE_SECONDS + 0.5)
        reclaimed = backend.acquire_run_lock(org_repo)
        assert reclaimed is not None
        assert reclaimed.holder_id != second.holder_id

        backend.release_lock(op_lock)
    finally:
        _delete_refs(org_repo)


@pytest.mark.live
def test_model_route_status_round_trips_against_a_real_global_ref():
    """Wave 8.6 (`OPS-011` extension): the first GLOBAL (not per-org_repo)
    ref this backend uses -- proves save/load round-trips for real, and that
    a second save (re-enable) correctly overwrites the prior status via the
    same CAS-retry mechanism `save_domain()` already uses one level down."""
    backend = GitStateBackend()
    job = f"live-test-job-{uuid.uuid4().hex[:8]}"
    try:
        assert backend.load_model_route_status(job) is None

        backend.save_model_route_status(
            ModelRouteStatusV1(job=job, status="disabled", reason="golden-set pass rate low")
        )
        disabled = backend.load_model_route_status(job)
        assert disabled is not None
        assert disabled.status == "disabled"

        backend.save_model_route_status(
            ModelRouteStatusV1(job=job, status="enabled", re_enabled_by="live-test")
        )
        enabled = backend.load_model_route_status(job)
        assert enabled is not None
        assert enabled.status == "enabled"
        assert enabled.re_enabled_by == "live-test"
    finally:
        # CAUTION: this deletes the ENTIRE global registry (every job's
        # status), not just this test's own job entry -- the minimal
        # save/load API this wave ships has no per-key delete. Safe today
        # only because nothing else has written to this brand-new ref yet;
        # revisit before this mechanism carries any real production status.
        run_git(["push", "origin", f":{MODEL_ROUTE_REF}"])


@pytest.mark.live
def test_stale_release_never_destroys_a_reclaimer_s_active_lock():
    """Production-reliability regression (found by independent review,
    2026-07-20): before the `--force-with-lease` fix, `release_lock()` did
    an unconditional `git push origin :{ref}` -- if a runner's own lease
    expired mid-operation (a slow LLM call, a retried GitHub API call) and a
    second runner legitimately reclaimed the lock in the meantime, the first
    runner's own (late, stale) `release_lock()` call would delete the
    SECOND runner's active lock, not its own (already-superseded) one,
    letting a third runner acquire while the second still believed it held
    exclusivity. Reproduced here with two real `GitStateBackend` instances
    (simulating two separate runners) against a real lock ref: runner A's
    lease is forced to an already-expired state on the real remote (the
    same observable state a genuine 900s overrun would eventually reach),
    runner B genuinely reclaims via the real CAS `acquire_lock()` path, and
    runner A's late `release_lock()` call is confirmed to leave runner B's
    lock untouched."""
    org_repo = _disposable_org_repo()
    runner_a = GitStateBackend()
    runner_b = GitStateBackend()
    try:
        first = runner_a.acquire_lock(org_repo)
        assert first is not None

        # Force the real remote lease into an already-expired state --
        # the same observable condition a genuine 900s overrun reaches,
        # without actually waiting 900s. runner_a's own in-memory `first`
        # Lock object is now stale relative to the real remote, exactly as
        # it would be after a real overrun.
        remote_ref = f"{LOCK_REF_PREFIX}/{_ref_key(org_repo)}"
        expired_payload = (
            json.dumps(
                {"holder_id": first.holder_id, "leased_until": "2020-01-01T00:00:00+00:00"},
                indent=2,
            )
            + "\n"
        )
        commit_sha = _write_commit(
            tree_path="lock.json",
            payload=expired_payload,
            parent_sha=None,
            message=f"lock: {org_repo} (test-forced-expiry)",
        )
        run_git(["push", "origin", f"{commit_sha}:{remote_ref}", "--force"])

        second = runner_b.acquire_lock(org_repo)
        assert second is not None
        assert second.holder_id != first.holder_id  # runner B genuinely holds it now

        # Runner A, unaware, finishes and releases its own (stale) lock.
        runner_a.release_lock(first)

        # The real remote lock ref must still be runner B's, untouched.
        current_sha = _fetch_remote_sha(remote_ref)
        assert current_sha is not None
        current_payload = json.loads(_read_blob(current_sha, "lock.json"))
        assert current_payload["holder_id"] == second.holder_id

        runner_b.release_lock(second)
    finally:
        _delete_refs(org_repo)
