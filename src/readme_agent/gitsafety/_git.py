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
    stdout/stderr are still decoded as text, matching every other call.

    A hung git subprocess (found live, 2026-07-22: `git push` blocking on
    interactive credential-manager resolution against a real HTTPS remote --
    a known hazard already documented in `test_state_git_backend_live.py`'s
    own docstring) previously surfaced as an uncaught `subprocess.
    TimeoutExpired`, crashing every caller with a raw traceback instead of the
    typed error each caller's own `if result.returncode != 0` branch already
    handles. Fixed once here, at the source every one of this function's ~20
    call sites shares, rather than patched at each call site separately: a
    timeout is reported as an ordinary failed `CompletedProcess` (conventional
    shell timeout exit code 124), so existing failure-handling logic
    everywhere picks it up unchanged."""
    full_env = {**os.environ, **env} if env else None
    git_args = ["git", *DETERMINISM_FLAGS, *args]
    try:
        if input_text is None:
            return subprocess.run(
                git_args,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=full_env,
            )
        raw = subprocess.run(
            git_args,
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
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=git_args,
            returncode=124,
            stdout="",
            stderr=f"git {' '.join(args)} timed out after {timeout}s",
        )
