"""The real `StateBackend` (`MEM-003`): one git ref per `org_repo`, on this
project's own remote -- never a target repo (decision #4's allow-list
governs what `readme-agent` may *operate on*, not where its own operational
state lives).

Deliberately one ref per repo, not one shared branch holding every repo's
state as separate files: git's non-fast-forward push rejection is scoped to
*the ref*, not to an individual path inside it. One shared branch would make
two unrelated repos' concurrent writes falsely conflict (whichever pushes
second is told `stale` even though nothing about its own repo's state
changed) -- a false positive on exactly the safety signal `MEM-002` exists to
produce. A per-repo ref makes that impossible by construction: unrelated
repos literally cannot collide, because they are different refs.

Deliberately no working-tree checkout per write -- git plumbing
(`hash-object`/`mktree`/`commit-tree`/`push <sha>:<ref>`) writes objects
directly into this repo's own already-checked-out `.git`, keyed off `FETCH_HEAD`
rather than a materialized tracking branch. A per-write checkout would
reintroduce exactly the "local clone as durable-state dependency" antipattern
this module exists to remove, just renamed.
"""

import json
import os
import socket
import sys
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from readme_agent.errors import StateBackendError
from readme_agent.gitsafety._git import run_git
from readme_agent.retry import RetryableOperationError, run_with_retry
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.migrations import ensure_run_state_v2, load_run_state_json
from readme_agent.state.schema import (
    ModelRouteRegistryV1,
    ModelRouteStatusV1,
    RunStateV1,
    RunStateV2,
)

STATE_REF_PREFIX = "refs/readme-agent-state"
LOCK_REF_PREFIX = "refs/readme-agent-state/locks"

# A stale lease is reclaimable so one crashed/timed-out runner can't
# permanently wedge a repo's state -- long enough for one generate_repo()
# run (clone + optional LLM call + validate), short enough that a genuine
# crash doesn't block the next scheduled run for long.
LOCK_LEASE_SECONDS = 900

# SCL-005 extension (Wave 8.5): a second, coarser, run-scoped lock ref,
# covering the whole supervise_repo() call (specialist tier through the
# planner loop), not just one narrow per-write section -- see
# GitStateBackend.acquire_run_lock()'s own docstring for why this closes a
# real lock-race this project's own SCL-005 row already named. A genuinely
# different ref than LOCK_REF_PREFIX, so it cannot self-deadlock against
# save_domain()'s own internal use of that lock. Own named constant (not a
# reused reference to LOCK_LEASE_SECONDS), free to diverge later -- no
# operational history yet to justify a different starting value.
RUN_LOCK_REF_PREFIX = "refs/readme-agent-state/run-locks"
RUN_LOCK_LEASE_SECONDS = 900

# Wave 8.6 (`OPS-011` extension): the first GLOBAL (not per-org_repo) ref in
# this codebase -- one record covers every LLM job route's enabled/disabled
# status, not scoped to any single repo.
MODEL_ROUTE_REF = "refs/readme-agent-state/model-routes"
_MODEL_ROUTE_SAVE_MAX_RETRIES = 5

# Pinned rather than relying on ambient git config, matching
# `_git.py::DETERMINISM_FLAGS`'s reasoning -- a GitHub Actions runner has no
# user identity configured by default, and this must not depend on one.
_COMMIT_IDENTITY_ENV = {
    "GIT_AUTHOR_NAME": "readme-agent",
    "GIT_AUTHOR_EMAIL": "readme-agent@noreply.local",
    "GIT_COMMITTER_NAME": "readme-agent",
    "GIT_COMMITTER_EMAIL": "readme-agent@noreply.local",
}


def _ref_key(org_repo: str) -> str:
    """Matches `paths.py`'s `{org}__{repo}` convention -- `org_repo` is
    always exactly one slash (`registry/models.py::ProductEntry.org_repo`)."""
    return org_repo.replace("/", "__", 1)


def _is_non_fast_forward(stderr: str) -> bool:
    lowered = stderr.lower()
    return any(
        marker in lowered
        for marker in ("non-fast-forward", "fetch first", "stale info", "already exists")
    )


def _fetch_remote_sha(remote_ref: str) -> str | None:
    """Returns the remote ref's current commit SHA, or `None` if the ref
    doesn't exist yet (first run for this repo) -- distinguished from any
    other fetch failure (network/auth), which raises rather than being
    silently treated as "no prior state" (fail-closed, decision #15's
    pattern applied here)."""
    result = run_git(["fetch", "origin", remote_ref])
    if result.returncode != 0:
        if "couldn't find remote ref" in result.stderr.lower():
            return None
        raise StateBackendError(f"fetch of {remote_ref} failed: {result.stderr}")
    rev = run_git(["rev-parse", "FETCH_HEAD"])
    if rev.returncode != 0:
        raise StateBackendError(
            f"rev-parse FETCH_HEAD failed after fetching {remote_ref}: {rev.stderr}"
        )
    return rev.stdout.strip()


def _read_blob(commit_sha: str, path: str) -> str:
    result = run_git(["cat-file", "-p", f"{commit_sha}:{path}"])
    if result.returncode != 0:
        raise StateBackendError(f"reading {path} from {commit_sha} failed: {result.stderr}")
    return result.stdout


def _write_commit(*, tree_path: str, payload: str, parent_sha: str | None, message: str) -> str:
    """`hash-object` -> `mktree` -> `commit-tree`, all via stdin, no working
    tree touched. Returns the new commit SHA."""
    blob = run_git(["hash-object", "-w", "--stdin"], input_text=payload)
    if blob.returncode != 0:
        raise StateBackendError(f"hash-object failed: {blob.stderr}")
    blob_sha = blob.stdout.strip()

    tree = run_git(["mktree"], input_text=f"100644 blob {blob_sha}\t{tree_path}\n")
    if tree.returncode != 0:
        raise StateBackendError(f"mktree failed: {tree.stderr}")
    tree_sha = tree.stdout.strip()

    commit_args = ["commit-tree", tree_sha, "-m", message]
    if parent_sha is not None:
        commit_args += ["-p", parent_sha]
    commit = run_git(commit_args, env=_COMMIT_IDENTITY_ENV)
    if commit.returncode != 0:
        raise StateBackendError(f"commit-tree failed: {commit.stderr}")
    return commit.stdout.strip()


def _acquire_lock_generic(
    ref_prefix: str, org_repo: str, tracking: dict[str, str], lease_seconds: int
) -> Lock | None:
    """Shared body for both lock families (Wave 8.5) -- parameterized on
    ref prefix, the instance's own tracking dict, and lease duration, read
    from the caller's own module-level constant at call time so
    `monkeypatch.setattr(git_backend, "LOCK_LEASE_SECONDS", ...)`/
    `"RUN_LOCK_LEASE_SECONDS"` keep working exactly as before this refactor."""
    remote_ref = f"{ref_prefix}/{_ref_key(org_repo)}"
    parent_sha = _fetch_remote_sha(remote_ref)

    if parent_sha is not None:
        existing = json.loads(_read_blob(parent_sha, "lock.json"))
        if datetime.fromisoformat(existing["leased_until"]) > datetime.now(UTC):
            return None  # held by someone else, not expired

    holder_id = f"{os.getpid()}@{socket.gethostname()}.{uuid4().hex[:8]}"
    leased_until = (datetime.now(UTC) + timedelta(seconds=lease_seconds)).isoformat()
    lock_payload = {"holder_id": holder_id, "leased_until": leased_until}
    payload = json.dumps(lock_payload, indent=2) + "\n"
    commit_sha = _write_commit(
        tree_path="lock.json",
        payload=payload,
        parent_sha=parent_sha,
        message=f"lock: {org_repo}",
    )

    push = run_git(["push", "origin", f"{commit_sha}:{remote_ref}"])
    if push.returncode != 0:
        if _is_non_fast_forward(push.stderr):
            return None  # lost the race to acquire/reclaim
        raise StateBackendError(f"push of {remote_ref} failed: {push.stderr}")

    tracking[org_repo] = commit_sha
    return Lock(org_repo=org_repo, holder_id=holder_id, leased_until=leased_until)


def _release_lock_generic(ref_prefix: str, lock: Lock, tracking: dict[str, str]) -> None:
    """Shared body for both lock families (Wave 8.5) -- see each public
    `release_lock`/`release_run_lock` method's own docstring for the
    compare-and-swap-delete reasoning this preserves unchanged."""
    remote_ref = f"{ref_prefix}/{_ref_key(lock.org_repo)}"
    expected_sha = tracking.pop(lock.org_repo, None)
    if expected_sha is None:
        print(
            f"warning: release_lock called for {lock.org_repo!r} with no locally-tracked "
            "lock commit -- refusing to delete blind, skipping",
            file=sys.stderr,
        )
        return

    push = run_git(
        ["push", "origin", f"--force-with-lease={remote_ref}:{expected_sha}", f":{remote_ref}"]
    )
    if push.returncode != 0 and not _is_non_fast_forward(push.stderr):
        raise StateBackendError(f"releasing lock {remote_ref} failed: {push.stderr}")


class GitStateBackend:
    """The one real `StateBackend` implementation (`MEM-003`'s "interface +
    at least one real backend" bar). Operates against `origin` in the
    current working directory -- this project's own repo, resolved the same
    cwd-relative way `paths.py` resolves `runs/` (local dev run from the
    repo root, GitHub Actions checkout puts cwd at the repo root)."""

    def __init__(self) -> None:
        # Wave 7 production-reliability fix (found by independent review,
        # 2026-07-20): `release_lock()` used to unconditionally delete
        # whatever the lock ref currently pointed to. If this instance's own
        # lease expired mid-operation (a slow LLM call, a retried GitHub API
        # call) and a second runner legitimately reclaimed the lock in the
        # meantime, that unconditional delete destroyed the SECOND runner's
        # active lock, not this (already-expired) one -- letting a third
        # runner acquire while the second still believed it held exclusivity.
        # Tracking the exact commit this instance created lets `release_
        # lock()` do a compare-and-swap delete instead (`--force-with-
        # lease`): it only ever removes the lock this instance itself put
        # there, never anyone else's. Instance-scoped, not persisted --
        # acquire and release always pair on the same backend instance
        # within one call (`supervisor/loop.py`'s `try/finally`).
        self._held_lock_commit_shas: dict[str, str] = {}
        # Wave 8.5 (SCL-005 extension): the run-lock's own tracking dict --
        # genuinely separate from the one above, since it's keyed only by
        # org_repo, not by lock-kind, and cannot safely hold both lock
        # families' state simultaneously for the same repo.
        self._held_run_lock_commit_shas: dict[str, str] = {}

    def load(self, org_repo: str) -> RunStateV2 | None:
        remote_ref = f"{STATE_REF_PREFIX}/{_ref_key(org_repo)}"
        sha = _fetch_remote_sha(remote_ref)
        if sha is None:
            return None
        return load_run_state_json(_read_blob(sha, "state.json"))

    def save(
        self,
        org_repo: str,
        state: RunStateV1 | RunStateV2,
        expected_version: int | None,
    ) -> SaveResult:
        remote_ref = f"{STATE_REF_PREFIX}/{_ref_key(org_repo)}"
        parent_sha = _fetch_remote_sha(remote_ref)

        if parent_sha is None:
            if expected_version is not None:
                # Caller believed prior state existed; it doesn't (or no
                # longer does) -- its expectation no longer describes reality.
                return SaveResult(outcome="stale", new_version=None)
            current_version = None
        else:
            current = load_run_state_json(_read_blob(parent_sha, "state.json"))
            if expected_version != current.state_version:
                return SaveResult(outcome="stale", new_version=current.state_version)
            current_version = current.state_version

        new_version = (current_version or 0) + 1
        new_state = ensure_run_state_v2(state).model_copy(
            update={"org_repo": org_repo, "state_version": new_version}
        )
        payload = json.dumps(new_state.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
        commit_sha = _write_commit(
            tree_path="state.json",
            payload=payload,
            parent_sha=parent_sha,
            message=f"state: {org_repo} v{new_version}",
        )

        push = run_git(["push", "origin", f"{commit_sha}:{remote_ref}"])
        if push.returncode != 0:
            if _is_non_fast_forward(push.stderr):
                return SaveResult(outcome="stale", new_version=None)
            raise StateBackendError(f"push of {remote_ref} failed: {push.stderr}")

        return SaveResult(outcome="saved", new_version=new_version)

    def acquire_lock(self, org_repo: str) -> Lock | None:
        return _acquire_lock_generic(
            LOCK_REF_PREFIX, org_repo, self._held_lock_commit_shas, LOCK_LEASE_SECONDS
        )

    def release_lock(self, lock: Lock) -> None:
        """Compare-and-swap delete (`--force-with-lease`), not a plain
        unconditional one -- verified live (2026-07-20) that git rejects a
        stale-expected-value delete with `stale info` in stderr, the exact
        same marker `_is_non_fast_forward()` already recognizes, whether the
        ref moved to someone else's commit or was already deleted entirely.
        Only ever removes the lock commit *this instance* created; if
        someone else has since reclaimed it (this instance's own lease
        genuinely expired), that rejection is the correct, safe outcome --
        not an error to raise."""
        _release_lock_generic(LOCK_REF_PREFIX, lock, self._held_lock_commit_shas)

    def lock_still_held(self, lock: Lock) -> bool:
        """Decision #46/#48 (`EFF-005`): re-fetch the lock ref fresh and
        compare `holder_id` -- the same identity `_acquire_lock_generic()`
        already stamps into every lease, never previously read back until
        now. Deliberately does NOT also re-check `leased_until` against
        wall-clock: a holder_id match already proves no one else has
        reclaimed this lease (the only way a *different* holder_id could
        appear is a successful competing acquire, which requires this ref to
        have been pushed to), so a lease that has technically ticked past
        its nominal duration but was never actually reclaimed is still
        genuinely exclusive -- treating it as lost here would be a false
        negative, not a safety improvement."""
        remote_ref = f"{LOCK_REF_PREFIX}/{_ref_key(lock.org_repo)}"
        sha = _fetch_remote_sha(remote_ref)
        if sha is None:
            return False
        current = json.loads(_read_blob(sha, "lock.json"))
        return bool(current.get("holder_id") == lock.holder_id)

    def acquire_run_lock(self, org_repo: str) -> Lock | None:
        """SCL-005 extension (Wave 8.5): a second, coarser, run-scoped lock,
        acquired once by `supervisor/loop.py::supervise_repo()` right after
        its first freshness shortcut, covering the specialist tier and the
        planner loop -- unlike the narrow per-write lock above (held only
        for the duration of one `save_domain()`/`dispatch_gated_effect()`
        call), this closes the real lock-race this project's own `SCL-005`
        row already named: two concurrent `supervise_repo()` calls for the
        same `org_repo` could previously both pay for the full specialist
        tier (including live GitHub API calls) before either was rejected,
        because the narrow lock was acquired only after that tier completed.
        A genuinely different git ref than `LOCK_REF_PREFIX` -- every
        acquisition on either ref is a non-blocking, immediate-return
        optimistic CAS (never a wait), so this cannot self-deadlock against
        `save_domain()`'s own internal use of the narrow lock, confirmed by
        direct reading of both call paths."""
        return _acquire_lock_generic(
            RUN_LOCK_REF_PREFIX, org_repo, self._held_run_lock_commit_shas, RUN_LOCK_LEASE_SECONDS
        )

    def release_run_lock(self, lock: Lock) -> None:
        _release_lock_generic(RUN_LOCK_REF_PREFIX, lock, self._held_run_lock_commit_shas)

    def _load_model_route_registry(self) -> ModelRouteRegistryV1 | None:
        sha = _fetch_remote_sha(MODEL_ROUTE_REF)
        if sha is None:
            return None
        return ModelRouteRegistryV1.model_validate_json(_read_blob(sha, "model_routes.json"))

    def load_model_route_status(self, job: str) -> ModelRouteStatusV1 | None:
        registry = self._load_model_route_registry()
        if registry is None:
            return None
        return registry.routes.get(job)

    def save_model_route_status(self, status: ModelRouteStatusV1) -> None:
        def attempt() -> None:
            sha = _fetch_remote_sha(MODEL_ROUTE_REF)
            current = (
                ModelRouteRegistryV1.model_validate_json(_read_blob(sha, "model_routes.json"))
                if sha is not None
                else ModelRouteRegistryV1()
            )
            updated = current.model_copy(
                update={
                    "routes": {**current.routes, status.job: status},
                    "state_version": current.state_version + 1,
                }
            )
            payload = json.dumps(updated.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
            commit_sha = _write_commit(
                tree_path="model_routes.json",
                payload=payload,
                parent_sha=sha,
                message=f"model-route: {status.job} -> {status.status}",
            )
            push = run_git(["push", "origin", f"{commit_sha}:{MODEL_ROUTE_REF}"])
            if push.returncode == 0:
                return
            if _is_non_fast_forward(push.stderr):
                raise RetryableOperationError("model-route CAS push was stale")
            raise StateBackendError(f"push of {MODEL_ROUTE_REF} failed: {push.stderr}")

        try:
            run_with_retry(
                "state_cas",
                attempt,
                max_attempts=_MODEL_ROUTE_SAVE_MAX_RETRIES,
            )
        except RetryableOperationError as exc:
            raise StateBackendError(
                f"save_model_route_status for {status.job!r} did not converge after "
                f"{_MODEL_ROUTE_SAVE_MAX_RETRIES} retries"
            ) from exc


def default_state_backend() -> GitStateBackend:
    return GitStateBackend()
