"""Pre-commit gate (GOV-033), Phase 1 -- advisory only: when a commit touches a
shared governance path, leave a short-lived trace on the same CAS backend
`mission_control.py`'s taskcard claims already use, so a concurrent agent's own
commit-time check can observe recent governance-write activity. This is the
smallest of a related trio of fixes; see the plan this implements for the other
two (a targeted dedicated-test gate, `validate_pinned_hash_dedicated_tests.py`;
and the still-open, separately-scoped durable-ratchet-tier work, Decision #112).

Deliberately reuses `GitStateBackend.acquire_governance_lock()`/
`peek_governance_lock()` -- a thin wrapper over the same `_acquire_lock_generic`
primitive already proven for two other lock families (`acquire_lock`,
`acquire_run_lock`) -- rather than inventing a fourth coordination mechanism.

Phase 1 behavior, by design: this NEVER blocks a commit and NEVER fails the
hook on a network/backend error (both this repo's real state remote being
briefly unreachable, and simple absence of network, must not brick an ordinary
commit). It prints an informational note when a lock is already held
(regardless of whether that's this same session's own recent activity or a
genuine peer -- Phase 1 does not attempt to distinguish the two; see the
plan's own notes on why that's deferred to Phase 2, which will need a stable
per-session identity to do it safely) and always leaves its own successful
acquisition to expire naturally via its lease rather than releasing
immediately -- an immediate release would erase the very trace a concurrent
session is meant to observe.

Run standalone: `.venv/Scripts/python scripts/governance/validate_governance_write_lock.py`
Always exits 0 in Phase 1.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GOVERNANCE_LOCK_KEY = "shared-governance-write"

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


def main() -> int:
    staged = staged_files()
    if not touches_protected_path(staged):
        return 0

    try:
        from readme_agent.state.git_backend import GitStateBackend

        with GitStateBackend() as backend:
            lock = backend.acquire_governance_lock(GOVERNANCE_LOCK_KEY)
            if lock is not None:
                print(
                    "validate_governance_write_lock: acquired shared-governance-write "
                    f"presence (leased_until={lock.leased_until}); this is advisory only "
                    "(Phase 1), not enforced."
                )
                return 0
            existing = backend.peek_governance_lock(GOVERNANCE_LOCK_KEY)
            if existing is not None:
                print(
                    "validate_governance_write_lock: note -- a shared-governance-write lock "
                    f"is currently active (holder={existing.get('holder_id')}, "
                    f"leased_until={existing.get('leased_until')}). If that is a different "
                    "session, coordinate before proceeding. Not blocked (Phase 1: advisory "
                    "only)."
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
