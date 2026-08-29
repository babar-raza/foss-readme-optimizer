"""Pre-commit gate (GOV-033/ACL-GOV-LOCK-ENFORCE). Phase 1 (default, unchanged):
advisory only -- when a commit touches a shared governance path, leave a
short-lived trace on the same CAS backend `mission_control.py`'s taskcard
claims already use, so a concurrent agent's own commit-time check can observe
recent governance-write activity. Phase 2 (opt-in via
`README_AGENT_GOVERNANCE_LOCK_ENFORCE=1`): actually blocks a commit when a
*different* session genuinely holds the lock. Both share one script so the
enforcing behavior is exercised by the same code path it will run in once
activated, not a parallel implementation that could drift.

Deliberately reuses `GitStateBackend.acquire_governance_lock()`/
`peek_governance_lock()` -- a thin wrapper over the same `_acquire_lock_generic`
primitive already proven for two other lock families (`acquire_lock`,
`acquire_run_lock`) -- rather than inventing a fourth coordination mechanism.
`_acquire_lock_generic` itself is untouched: Phase 2's "is this still me"
distinction is solved entirely in this script, using only local state, so nothing
here can affect `acquire_lock`/`acquire_run_lock`'s existing, separately-tested
behavior.

The problem Phase 1 could not safely solve: `acquire_governance_lock()`
generates a fresh, opaque `holder_id` on every call, so nothing distinguishes
"this same session, acquiring again a moment later" from "a genuine peer" --
blocking on that alone would lock a session out of its *own* follow-up commits
for the lease's full 900 seconds. Fixed without touching the lock schema: this
script now records the holder_id of its own last successful acquisition in a
worktree-local file (resolved via `git rev-parse --git-dir`, so two worktrees
of the same clone -- this project's own parallel-lane pattern -- never share
one one file and never see each other as "the same session"). On the next
check, an active lock whose holder_id matches that local record is *this
session, still within its own lease* and never blocks; an active lock with
any other holder_id is a genuine peer.

Phase 2, when enabled, still never fails the hook on a network/backend error
(this repo's real state remote being briefly unreachable, or simple absence
of network, must never brick an ordinary commit) -- only an actively-held
lock from a genuine peer blocks. Phase 1 (the default) is unchanged: it never
blocks, and always leaves its own acquisition to expire naturally via its
lease rather than releasing immediately, so the trace a concurrent session
would want to see survives.

Enabling Phase 2 for real requires *also* adding `|| exit 1` after this
script's invocation in the hook template
(`scripts/governance/install_hooks.py`) and reinstalling hooks -- deliberately
not done as part of landing this capability. See the plan/log entry that
introduced this for why: this is the riskiest change to shared commit
infrastructure in that plan, and activating it deserves its own deliberate
step with the concurrent-process integration test
(`test_validate_governance_write_lock.py`) as evidence, not a silent default
flip bundled with something else.

Run standalone: `.venv/Scripts/python scripts/governance/validate_governance_write_lock.py`
Exits 0 always in Phase 1 (default); exits 1 only in Phase 2
(`README_AGENT_GOVERNANCE_LOCK_ENFORCE=1`) when a genuine peer holds the lock.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GOVERNANCE_LOCK_KEY = "shared-governance-write"
ENFORCE_ENV_VAR = "README_AGENT_GOVERNANCE_LOCK_ENFORCE"

PROTECTED_PATH_PREFIXES = ("plans/", "logs/")
PROTECTED_PATHS = (
    "AGENTS.md",
    "plans/investigations/control/level8-autonomous-mission-task-graph.yaml",
)


def staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def touches_protected_path(staged_paths: list[str]) -> bool:
    return any(
        path in PROTECTED_PATHS or path.startswith(PROTECTED_PATH_PREFIXES) for path in staged_paths
    )


def _worktree_git_dir(cwd: Path | None = None) -> Path | None:
    """Resolves to `.git` for the main tree, or `.git/worktrees/<name>` for a
    linked worktree -- never the same path for two worktrees of one clone."""

    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return (cwd or REPO_ROOT) / result.stdout.strip()


def _last_own_holder_path(cwd: Path | None = None) -> Path | None:
    git_dir = _worktree_git_dir(cwd)
    if git_dir is None:
        return None
    return git_dir / "readme-agent-last-governance-lock-holder"


def _record_own_holder(holder_id: str, cwd: Path | None = None) -> None:
    marker = _last_own_holder_path(cwd)
    if marker is not None:
        marker.write_text(holder_id, encoding="utf-8")


def _read_own_last_holder(cwd: Path | None = None) -> str | None:
    marker = _last_own_holder_path(cwd)
    if marker is not None and marker.is_file():
        return marker.read_text(encoding="utf-8").strip()
    return None


def main(cwd: Path | None = None) -> int:
    staged = staged_files()
    if not touches_protected_path(staged):
        return 0
    enforce = os.environ.get(ENFORCE_ENV_VAR) == "1"

    try:
        from readme_agent.state.git_backend import GitStateBackend

        with GitStateBackend() as backend:
            lock = backend.acquire_governance_lock(GOVERNANCE_LOCK_KEY)
            if lock is not None:
                _record_own_holder(lock.holder_id, cwd)
                print(
                    "validate_governance_write_lock: acquired shared-governance-write "
                    f"presence (leased_until={lock.leased_until})"
                    + ("" if enforce else "; advisory only (Phase 1), not enforced.")
                )
                return 0
            existing = backend.peek_governance_lock(GOVERNANCE_LOCK_KEY)
            if existing is None:
                return 0
            existing_holder = existing.get("holder_id")
            is_own = enforce and existing_holder == _read_own_last_holder(cwd)
            if enforce and not is_own:
                print(
                    "validate_governance_write_lock: BLOCKED -- a shared-governance-write "
                    f"lock is held by a different session (holder={existing_holder}, "
                    f"leased_until={existing.get('leased_until')}). Coordinate before "
                    "proceeding, or wait for the lease to expire.",
                    file=sys.stderr,
                )
                return 1
            print(
                "validate_governance_write_lock: note -- a shared-governance-write lock "
                f"is currently active (holder={existing_holder}, "
                f"leased_until={existing.get('leased_until')})."
                + (
                    " This is this session's own recent acquisition; proceeding."
                    if is_own
                    else " If that is a different session, coordinate before proceeding. "
                    "Not blocked (Phase 1: advisory only)."
                )
            )
            return 0
    except Exception as exc:  # noqa: BLE001 - must never brick an ordinary commit
        print(
            f"validate_governance_write_lock: skipped (backend unavailable: {exc!r}); "
            "advisory-only check, not blocking.",
            file=sys.stderr,
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
