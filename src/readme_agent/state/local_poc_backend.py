"""Provide the durable local Git-ref backend used by the rapid POC profile."""

from __future__ import annotations

import os
from pathlib import Path

from filelock import FileLock

from readme_agent.errors import StateBackendError
from readme_agent.gitsafety._git import run_git
from readme_agent.state.git_backend import GitStateBackend


def local_poc_state_remote() -> str:
    """Return an explicit override or initialize the repository-local bare state remote."""

    override = os.environ.get("README_AGENT_STATE_REMOTE")
    if override:
        return override

    remote = (Path("runs") / "local-poc-state" / "state.git").resolve()
    remote.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(remote.parent / "state-init.lock")):
        if not remote.exists():
            result = run_git(["init", "--bare", str(remote)], cwd=remote.parent)
            if result.returncode != 0:
                raise StateBackendError(
                    f"initializing local POC state remote failed: {result.stderr}"
                )
        check = run_git(
            ["--git-dir", str(remote), "rev-parse", "--is-bare-repository"],
            cwd=remote.parent,
        )
        if check.returncode != 0 or check.stdout.strip() != "true":
            raise StateBackendError(
                f"local POC state remote is not a bare Git repository: {remote}"
            )
    return str(remote)


def default_local_poc_state_backend() -> GitStateBackend:
    """Build a durable backend that never defaults local POC state writes to `origin`."""

    return GitStateBackend(remote=local_poc_state_remote())
