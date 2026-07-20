"""Small subprocess wrapper shared by the gitsafety modules."""

import os
import subprocess
from pathlib import Path

# Pinned per-invocation (never relies on the operator's/runner's ambient git
# config) -- see the plan's "Consistency & Determinism" Tier 1 SS3: this is the
# fix for cross-platform (Windows dev / Linux CI) line-ending nondeterminism at
# the source, not just at the hashing layer.
DETERMINISM_FLAGS = ["-c", "core.autocrlf=false", "-c", "core.eol=lf"]


def run_git(
    args: list[str],
    cwd: Path | None = None,
    timeout: float = 120,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """input_text/env are for `state/git_backend.py`'s plumbing calls
    (`hash-object --stdin`, `mktree`, `commit-tree` needing a pinned
    author/committer identity) -- every other caller leaves both `None`,
    unchanged from before these params existed.

    When `input_text` is given, stdin is piped as raw UTF-8 bytes rather than
    through `subprocess.run(text=True)`'s own stdin encoding: that path
    applies universal-newlines translation on *write* too, silently turning
    every `\\n` into `os.linesep` (`\\r\\n` on Windows) before it reaches
    git. For `mktree`'s tab/newline-delimited input that corrupts the tree
    entry itself -- a real bug found live (`refs/readme-agent-state/...`
    tree entries came back path `"state.json\\r"`, not `state.json`) --
    proven live in `tests/integration/test_state_git_backend_live.py`.
    stdout/stderr are still decoded as text, matching every other call."""
    full_env = {**os.environ, **env} if env else None
    if input_text is None:
        return subprocess.run(
            ["git", *DETERMINISM_FLAGS, *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=full_env,
        )
    raw = subprocess.run(
        ["git", *DETERMINISM_FLAGS, *args],
        cwd=str(cwd) if cwd else None,
        input=input_text.encode("utf-8"),
        capture_output=True,
        timeout=timeout,
        env=full_env,
    )
    return subprocess.CompletedProcess(
        args=raw.args,
        returncode=raw.returncode,
        stdout=raw.stdout.decode("utf-8", errors="replace"),
        stderr=raw.stderr.decode("utf-8", errors="replace"),
    )
