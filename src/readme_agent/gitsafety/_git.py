"""Small subprocess wrapper shared by the gitsafety modules."""

import subprocess
from pathlib import Path

# Pinned per-invocation (never relies on the operator's/runner's ambient git
# config) -- see the plan's "Consistency & Determinism" Tier 1 SS3: this is the
# fix for cross-platform (Windows dev / Linux CI) line-ending nondeterminism at
# the source, not just at the hashing layer.
DETERMINISM_FLAGS = ["-c", "core.autocrlf=false", "-c", "core.eol=lf"]


def run_git(
    args: list[str], cwd: Path | None = None, timeout: float = 120
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *DETERMINISM_FLAGS, *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
