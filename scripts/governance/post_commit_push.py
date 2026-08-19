"""Push this repository's own commits to its own `origin` automatically, immediately after they
land -- the mechanical half of GOVERNANCE.md rule 10's control-repo carve-out (Decision #107).

Distinct from `src/readme_agent/gitsafety/`, which blocks push on *product*-repo work clones. This
script does the opposite for *this* repository's own remote: it pushes, deliberately and only for
this checkout's own `origin`. Never imports `src/readme_agent` -- this stays standalone, exactly
like every other file in `scripts/governance/`.

Invoked by the `post-commit` hook `scripts/governance/install_hooks.py` installs. Never rewrites
history and never force-pushes: a rejected (non-fast-forward) push is reported, not retried, so a
concurrent-session race (a second session already pushed since this branch last synced) always
surfaces loudly instead of silently overwriting shared history.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The marker `gitsafety/neuter.py` writes into a disposable product work-clone's push URL. If this
# checkout's origin ever carries it, something is very wrong (this should never be a work clone) --
# refuse rather than push, instead of trusting a URL that shouldn't be here.
DISABLED_PUSH_URL = "DISABLED"

# `gitsafety/_git.py::run_git()`'s own docstring documents a real, live-found hang (2026-07-22):
# a `git push` blocking forever on an interactive credential-manager GUI prompt when it needs
# credentials it doesn't have. This hook runs unattended after every commit, so the identical
# hazard applies here -- `GIT_TERMINAL_PROMPT=0` closes git's own raw fallback prompt, and
# `GCM_INTERACTIVE=never` is git-credential-manager's own documented "fail instead of prompting"
# switch, the fix that specific incident needed (`GIT_TERMINAL_PROMPT=0` alone was proven
# insufficient). Duplicated here, not imported from `_git.py`, to keep this script standalone (no
# `src/readme_agent` import) -- same two literal values, deliberately not re-exported for a
# two-line duplication.
_GIT_SAFETY_ENV = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}

_NON_FAST_FORWARD_MARKERS = (
    "non-fast-forward",
    "fetch first",
    "rejected",
)


@dataclass
class PushResult:
    ok: bool
    branch: str | None
    detail: str


def _run_git(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, **_GIT_SAFETY_ENV},
    )


def current_branch(repo_root: Path = REPO_ROOT) -> str | None:
    """The checked-out branch name, or None on detached HEAD -- nothing to push to."""

    result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    return None if branch in ("", "HEAD") else branch


def _origin_push_url(repo_root: Path) -> str | None:
    result = _run_git(["remote", "get-url", "--push", "origin"], cwd=repo_root)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _toplevel_matches(repo_root: Path) -> bool:
    """Safety guard, same pattern as `gitsafety/clone.py::toplevel_matches()`: confirm git will
    actually operate on `repo_root` before pushing anything, not a parent/wrong repo."""

    result = _run_git(["rev-parse", "--show-toplevel"], cwd=repo_root)
    if result.returncode != 0:
        return False
    return Path(result.stdout.strip()).resolve() == repo_root.resolve()


def push_current_branch(repo_root: Path = REPO_ROOT) -> PushResult:
    branch = current_branch(repo_root)
    if branch is None:
        return PushResult(ok=True, branch=None, detail="detached HEAD -- nothing to push, skipped")

    if not _toplevel_matches(repo_root):
        return PushResult(
            ok=False,
            branch=branch,
            detail=f"{repo_root} is not git's own toplevel -- refusing to push (safety guard)",
        )

    push_url = _origin_push_url(repo_root)
    if push_url == DISABLED_PUSH_URL:
        return PushResult(
            ok=False,
            branch=branch,
            detail=(
                "origin's push URL is the product-repo neuter marker (DISABLED) -- refusing to "
                "push; this checkout should never be a neutered work clone"
            ),
        )

    result = _run_git(["push", "origin", branch], cwd=repo_root)
    if result.returncode == 0:
        return PushResult(ok=True, branch=branch, detail=f"pushed {branch} to origin")

    stderr = result.stderr
    if any(marker in stderr for marker in _NON_FAST_FORWARD_MARKERS):
        return PushResult(
            ok=False,
            branch=branch,
            detail=(
                f"push rejected (origin/{branch} has moved -- likely a concurrent session): "
                f"run 'git pull --rebase origin {branch}' then push again. Never force-pushed. "
                f"git stderr: {stderr.strip()}"
            ),
        )
    return PushResult(ok=False, branch=branch, detail=f"push failed: {stderr.strip()}")


def main() -> int:
    result = push_current_branch()
    print(f"post-commit push: {result.detail}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
