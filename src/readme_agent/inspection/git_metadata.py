"""Git metadata extraction from a local clone -- no LLM, no network beyond what's already cloned."""

from dataclasses import dataclass
from pathlib import Path

from readme_agent.gitsafety._git import run_git


@dataclass
class GitMetadata:
    remote_url: str | None
    branch: str | None
    commit_sha: str | None


def get_git_metadata(repo_path: Path) -> GitMetadata:
    remote = run_git(["remote", "get-url", "origin"], cwd=repo_path, timeout=10)
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path, timeout=10)
    sha = run_git(["rev-parse", "HEAD"], cwd=repo_path, timeout=10)
    return GitMetadata(
        remote_url=remote.stdout.strip() if remote.returncode == 0 else None,
        branch=branch.stdout.strip() if branch.returncode == 0 else None,
        commit_sha=sha.stdout.strip() if sha.returncode == 0 else None,
    )
