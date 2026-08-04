"""Disposable bare Git workspace for durable-state plumbing commands."""

from __future__ import annotations

import tempfile
from pathlib import Path

from filelock import FileLock

from readme_agent.errors import StateBackendError
from readme_agent.gitsafety._git import run_git


def resolve_state_remote(remote: str) -> str:
    """Resolve a checkout-local remote name before entering isolated plumbing."""

    if "://" in remote or Path(remote).is_absolute():
        return remote
    resolved = run_git(["remote", "get-url", remote])
    if resolved.returncode != 0:
        return remote
    target = resolved.stdout.strip()
    if not target:
        raise StateBackendError(f"state remote {remote!r} resolved to an empty URL")
    local_target = Path(target)
    if "://" not in target and local_target.exists():
        return str(local_target.resolve())
    return target


class StateGitWorkspace:
    """One process-local bare object/ref database for state Git plumbing."""

    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="readme-agent-state-")
        self.root = Path(self._temporary.name)
        self.git_dir = self.root / "plumbing.git"
        initialized = run_git(["init", "--bare", str(self.git_dir)], cwd=self.root)
        if initialized.returncode != 0:
            self._temporary.cleanup()
            raise StateBackendError(
                f"initializing isolated state Git workspace failed: {initialized.stderr}"
            )
        self.lock = FileLock(str(self.root / "plumbing.lock"))

    def cleanup(self) -> None:
        """Release the disposable local object/ref database."""

        self._temporary.cleanup()
