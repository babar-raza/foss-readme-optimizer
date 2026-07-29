"""Reuse a persistent baseline only after strict source and cleanliness verification."""

from __future__ import annotations

from pathlib import Path

from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import clone_baseline, record_baseline_clone_revision
from readme_agent.registry.models import ProductEntry


def verified_baseline_at_revision(
    entry: ProductEntry,
    baseline_path: Path,
    *,
    expected_revision: str,
) -> Path:
    """Return a clean matching baseline, otherwise replace it through the clone contract."""

    if _matches(entry, baseline_path, expected_revision):
        record_baseline_clone_revision(baseline_path, expected_revision)
        return baseline_path
    return clone_baseline(entry, baseline_path)


def _matches(entry: ProductEntry, baseline_path: Path, expected_revision: str) -> bool:
    if not baseline_path.is_dir() or not (baseline_path / ".git").exists():
        return False
    revision = run_git(["rev-parse", "HEAD"], cwd=baseline_path, timeout=10)
    if revision.returncode != 0 or revision.stdout.strip() != expected_revision:
        return False
    origin = run_git(["remote", "get-url", "origin"], cwd=baseline_path, timeout=10)
    if origin.returncode != 0 or origin.stdout.strip() != entry.clone_url:
        return False
    status = run_git(
        ["status", "--porcelain=v1", "--untracked-files=all"],
        cwd=baseline_path,
        timeout=30,
    )
    return status.returncode == 0 and not status.stdout.strip()
