"""One-time installer for this project's own (not a work-clone's) pre-commit hook.

Distinct from `src/readme_agent/gitsafety/hooks.py`, which installs a pre-push hook into every
disposable *work clone* the tool creates against a *target* repo. This installs a pre-commit hook
into *this* repository's own `.git/hooks/`, running `validate_plan_structure.py` before every
local commit -- Decision #46's "disallow from the start" mechanism, not just a CI-time check.

Run once per clone: `python scripts/governance/install_hooks.py`
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

HOOK_SCRIPT = """#!/bin/sh
# Decision #46: mechanical structural-integrity gate, installed via
# scripts/governance/install_hooks.py. Rejects a commit that breaks
# plans/master.md's section order, plans/requirements.md's row validity,
# logs/ index consistency, or specialist/docs-architecture module-map
# completeness. Backstopped by the same check as a required CI step for
# any commit made with --no-verify or from a clone without this hook.
if [ -x ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python"
fi
"$PYTHON" scripts/governance/validate_plan_structure.py
"""


def install_pre_commit_hook() -> Path:
    hook_path = REPO_ROOT / ".git" / "hooks" / "pre-commit"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(HOOK_SCRIPT, encoding="utf-8", newline="\n")
    try:
        current = os.stat(hook_path).st_mode
        os.chmod(hook_path, current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        # NTFS has no meaningful executable bit; Git for Windows invokes hooks via its
        # bundled shell based on the shebang regardless -- same posture as gitsafety/hooks.py.
        pass
    return hook_path


def main() -> int:
    hook_path = install_pre_commit_hook()
    print(f"Installed pre-commit hook at {hook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
