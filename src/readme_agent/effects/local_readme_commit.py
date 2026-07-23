"""Create the verified README commit in a push-disabled local work clone."""

from pathlib import Path

from readme_agent.gitsafety._git import run_git


def commit_verified_readme(work_path: Path, facts_hash: str, status: str, *, mode: str) -> bool:
    """Commit only a verified generated candidate in a full-mode work clone."""

    if mode != "full" or status != "GENERATED":
        return False
    run_git(["add", "-A"], cwd=work_path)
    commit = run_git(
        ["commit", "-m", f"readme-agent: close promotional gaps ({facts_hash[:12]})"],
        cwd=work_path,
    )
    return commit.returncode == 0
