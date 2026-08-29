"""One-time installer for this project's own (not a work-clone's) git hooks: `pre-commit` and
`post-commit`.

Distinct from `src/readme_agent/gitsafety/hooks.py`, which installs a pre-push hook into every
disposable *work clone* the tool creates against a *target* repo. This installs hooks into *this*
repository's own `.git/hooks/`:

- `pre-commit` runs `validate_plan_structure.py`, `ruff check`, `ruff format --check`, and
  `mypy src` before every local commit -- Decision #46/#48's "disallow from the start" mechanism,
  not just a CI-time check. The full pytest suite is deliberately not included (see
  PRE_COMMIT_HOOK_SCRIPT's own comment for why) and remains a required CI step instead. Two more,
  narrow, targeted steps follow (both GOV-033, 2026-08-29):
  `validate_pinned_hash_dedicated_tests.py` runs only the one or two pytest node ids
  relevant to files actually staged in this commit, for
  pins that have their own dedicated test instead of the `validate_pinned_hashes.py` registry
  (blocking -- this is a correctness gate); `validate_governance_write_lock.py` leaves an
  advisory, self-expiring trace on the shared CAS backend when a commit touches `plans/`, `logs/`,
  `AGENTS.md`, or the mission graph, so a concurrent agent's own check can see recent governance
  activity (Phase 1: informational only, never blocks).
- `post-commit` pushes the landed commit to this repository's own `origin` automatically, via
  `post_commit_push.py` -- Decision #107's mechanical enforcement of GOVERNANCE.md rule 10's
  control-repo carve-out. Never touches any product repo; never force-pushes.

Run once per clone: `python scripts/governance/install_hooks.py`
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PRE_COMMIT_HOOK_SCRIPT = """#!/bin/sh
# Decision #46/#48: mechanical structural-integrity + code-quality gate,
# installed via scripts/governance/install_hooks.py. Rejects a commit that
# breaks plans/master.md's section order, plans/requirements.md's row
# validity, logs/ index consistency, specialist/docs-architecture module-map
# completeness, ruff lint/format, or mypy types.
#
# The full pytest suite is deliberately NOT run here: as of 2026-07-22 it
# takes ~9 minutes (867 tests). A 9-minute pre-commit hook would get bypassed
# with --no-verify as a matter of routine, which defeats the entire
# "disallow from the start" point of a pre-commit gate. pytest remains a
# required CI step (ci.yml) instead, which is the right tradeoff for a check
# that slow: fast, deterministic, offline checks block the commit itself;
# the full suite blocks the push/PR. This is a deliberate scope narrowing
# from an earlier plan draft that called for pytest in this hook too -- see
# plans/master.md's Decision Ledger for the current record of this choice.
if [ -x ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python"
fi
"$PYTHON" scripts/governance/validate_plan_structure.py || exit 1
"$PYTHON" -m ruff check . || exit 1
"$PYTHON" -m ruff format --check . || exit 1
"$PYTHON" -m mypy src || exit 1
# GOV-033 (2026-08-29): targeted pin-drift gate for pins with their own dedicated
# test (e.g. the vendored check-battery manifest) -- only runs the specific node
# id(s) relevant to files staged in *this* commit, not the full suite. Blocking:
# a failure here means a real, uncommitted re-pin is needed.
"$PYTHON" scripts/governance/validate_pinned_hash_dedicated_tests.py || exit 1
# GOV-033 (2026-08-29): advisory-only governance-write presence trace on the
# shared CAS backend. Never blocks (Phase 1) -- deliberately no `|| exit 1`.
"$PYTHON" scripts/governance/validate_governance_write_lock.py
"""

POST_COMMIT_HOOK_SCRIPT = """#!/bin/sh
# Decision #107: push this repository's own commits to its own origin
# automatically, immediately after they land -- the mechanical half of
# GOVERNANCE.md rule 10's control-repo carve-out. Never touches any product
# repo (see src/readme_agent/gitsafety/ for that -- separate, untouched by
# this). Never force-pushes: post_commit_push.py reports a rejected
# (non-fast-forward) push instead of retrying it, so a concurrent-session
# race surfaces loudly rather than silently overwriting shared history. A
# failure here never loses the commit -- it already landed locally; the next
# successful push (this hook's next run, or a manual `git push`) carries it
# forward.
if [ -x ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python"
fi
"$PYTHON" scripts/governance/post_commit_push.py
"""


def _install_hook(name: str, script: str, repo_root: Path = REPO_ROOT) -> Path:
    hook_path = repo_root / ".git" / "hooks" / name
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(script, encoding="utf-8", newline="\n")
    try:
        current = os.stat(hook_path).st_mode
        os.chmod(hook_path, current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        # NTFS has no meaningful executable bit; Git for Windows invokes hooks via its
        # bundled shell based on the shebang regardless -- same posture as gitsafety/hooks.py.
        pass
    return hook_path


def install_pre_commit_hook(repo_root: Path = REPO_ROOT) -> Path:
    return _install_hook("pre-commit", PRE_COMMIT_HOOK_SCRIPT, repo_root)


def install_post_commit_hook(repo_root: Path = REPO_ROOT) -> Path:
    return _install_hook("post-commit", POST_COMMIT_HOOK_SCRIPT, repo_root)


def main() -> int:
    for hook_path in (install_pre_commit_hook(), install_post_commit_hook()):
        print(f"Installed {hook_path.name} hook at {hook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
