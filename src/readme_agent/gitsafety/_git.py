"""Small subprocess wrapper shared by the gitsafety modules."""

import os
import subprocess
from pathlib import Path

from readme_agent.gitsafety.process import run_bounded

# Pinned per-invocation (never relies on the operator's/runner's ambient git
# config) -- see the plan's "Consistency & Determinism" Tier 1 SS3: this is the
# fix for cross-platform (Windows dev / Linux CI) line-ending nondeterminism at
# the source, not just at the hashing layer.
DETERMINISM_FLAGS = ["-c", "core.autocrlf=false", "-c", "core.eol=lf"]

# Fixes the OTHER hung-git incident (`OPS-009`, found 2026-07-19 -- see
# `test_state_git_backend_live.py`'s own docstring): git resolving that it
# needs credentials it doesn't have can invoke an interactive credential
# helper (`git-credential-manager.exe` on Windows, confirmed live via
# `tasklist` to survive as a detached process even after the immediate child
# was killed) and block on stdin forever. A timeout alone cannot reliably
# bound this: CPython's own `subprocess.run()`, on `TimeoutExpired`, calls
# `process.kill()` then -- on Windows -- calls `process.communicate()` a
# SECOND time with NO timeout to drain buffered output before re-raising;
# that second, unbounded call joins reader threads still blocked in a plain
# `fh.read()` on the child's stdout/stderr pipes, which only returns once
# every process holding that pipe's write end closes it. If a detached
# credential-helper grandchild inherited the same handle and is still alive,
# that read blocks forever -- `run_git()`'s own `except subprocess.
# TimeoutExpired` below never even gets a chance to fire, because
# `subprocess.run()` itself never returns. `GIT_TERMINAL_PROMPT=0` closes
# this at the source instead: git fails fast and cleanly (non-zero exit, a
# stderr message like "could not read Username ... terminal prompts
# disabled"), never invoking a helper or touching stdin. Merged in LAST
# (after any caller-supplied `env`) so no call site can accidentally
# re-enable prompting -- confirmed by direct reading of `gitsafety/clone.py`,
# `gitsafety/neuter.py`, and `state/git_backend.py` that none of `run_git()`'s
# ~20 call sites relies on git prompting or on this var being unset; every
# one already treats a non-zero returncode as an ordinary handled failure.
#
# `GIT_TERMINAL_PROMPT=0` alone proved INSUFFICIENT -- found live, 2026-07-22,
# re-testing this exact fix: it only suppresses git's own raw fallback
# prompt. When a CONFIGURED credential helper exists (`git-credential-
# manager`, common on Windows -- confirmed present on this machine via
# `tasklist`), git invokes that helper regardless of `GIT_TERMINAL_PROMPT`,
# and the helper's own interactive (browser/GUI) flow is what actually hung
# -- reproduced live, killed via `taskkill`, and confirmed the run-lock this
# process held stayed correctly held until lease expiry (the reclaim safety
# net working exactly as designed for a hard kill, not just a caught
# exception). `GCM_INTERACTIVE=never` is git-credential-manager's own
# documented "fail instead of prompting" switch -- deliberately NOT a blanket
# `credential.helper=` override, which would also break the legitimate local-
# dev case (`test_state_git_backend_live.py`'s own documented prerequisite:
# a real, already-cached credential helper silently supplying push
# credentials with zero interaction) that this project still relies on.
GIT_SAFETY_ENV = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}


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
    full_env = {**os.environ, **(env or {}), **GIT_SAFETY_ENV}
    git_args = ["git", *DETERMINISM_FLAGS, *args]
    result = run_bounded(
        git_args,
        cwd=cwd,
        timeout=timeout,
        input_bytes=input_text.encode("utf-8") if input_text is not None else None,
        env=full_env,
    )
    if result.returncode == 124:
        return subprocess.CompletedProcess(
            args=git_args,
            returncode=124,
            stdout=result.stdout,
            stderr=f"git {' '.join(args)} timed out after {timeout}s",
        )
    return result
