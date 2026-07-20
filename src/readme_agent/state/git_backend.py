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
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from readme_agent.errors import StateBackendError
from readme_agent.gitsafety._git import run_git
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.schema import RunStateV1

STATE_REF_PREFIX = "refs/readme-agent-state"
LOCK_REF_PREFIX = "refs/readme-agent-state/locks"

# A stale lease is reclaimable so one crashed/timed-out runner can't
# permanently wedge a repo's state -- long enough for one generate_repo()
# run (clone + optional LLM call + validate), short enough that a genuine
# crash doesn't block the next scheduled run for long.
LOCK_LEASE_SECONDS = 900

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


class GitStateBackend:
    """The one real `StateBackend` implementation (`MEM-003`'s "interface +
    at least one real backend" bar). Operates against `origin` in the
    current working directory -- this project's own repo, resolved the same
    cwd-relative way `paths.py` resolves `runs/` (local dev run from the
    repo root, GitHub Actions checkout puts cwd at the repo root)."""

    def load(self, org_repo: str) -> RunStateV1 | None:
        remote_ref = f"{STATE_REF_PREFIX}/{_ref_key(org_repo)}"
        sha = _fetch_remote_sha(remote_ref)
        if sha is None:
            return None
        return RunStateV1.model_validate_json(_read_blob(sha, "state.json"))

    def save(self, org_repo: str, state: RunStateV1, expected_version: int | None) -> SaveResult:
        remote_ref = f"{STATE_REF_PREFIX}/{_ref_key(org_repo)}"
        parent_sha = _fetch_remote_sha(remote_ref)

        if parent_sha is None:
            if expected_version is not None:
                # Caller believed prior state existed; it doesn't (or no
                # longer does) -- its expectation no longer describes reality.
                return SaveResult(outcome="stale", new_version=None)
            current_version = None
        else:
            current = RunStateV1.model_validate_json(_read_blob(parent_sha, "state.json"))
            if expected_version != current.state_version:
                return SaveResult(outcome="stale", new_version=current.state_version)
            current_version = current.state_version

        new_version = (current_version or 0) + 1
        new_state = state.model_copy(update={"org_repo": org_repo, "state_version": new_version})
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
        remote_ref = f"{LOCK_REF_PREFIX}/{_ref_key(org_repo)}"
        parent_sha = _fetch_remote_sha(remote_ref)

        if parent_sha is not None:
            existing = json.loads(_read_blob(parent_sha, "lock.json"))
            if datetime.fromisoformat(existing["leased_until"]) > datetime.now(UTC):
                return None  # held by someone else, not expired

        holder_id = f"{os.getpid()}@{socket.gethostname()}.{uuid4().hex[:8]}"
        leased_until = (datetime.now(UTC) + timedelta(seconds=LOCK_LEASE_SECONDS)).isoformat()
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

        return Lock(org_repo=org_repo, holder_id=holder_id, leased_until=leased_until)

    def release_lock(self, lock: Lock) -> None:
        remote_ref = f"{LOCK_REF_PREFIX}/{_ref_key(lock.org_repo)}"
        push = run_git(["push", "origin", f":{remote_ref}"])
        if push.returncode != 0 and "remote ref does not exist" not in push.stderr.lower():
            raise StateBackendError(f"releasing lock {remote_ref} failed: {push.stderr}")


def default_state_backend() -> GitStateBackend:
    return GitStateBackend()
