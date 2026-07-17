"""Push-neutering: the first of two independent, defense-in-depth controls."""

from pathlib import Path

from readme_agent.errors import GitSafetyError
from readme_agent.gitsafety._git import run_git

DISABLED_PUSH_URL = "DISABLED"


def neuter_push(repo_path: Path) -> None:
    result = run_git(["remote", "set-url", "--push", "origin", DISABLED_PUSH_URL], cwd=repo_path)
    if result.returncode != 0:
        raise GitSafetyError(f"failed to neuter push remote in {repo_path}: {result.stderr}")
