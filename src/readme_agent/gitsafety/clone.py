"""Baseline (read-only reference) and work (mutable, disposable) clones.

Only read-only git verbs (clone, fetch) are ever issued against a real remote
here -- push is neutered separately in neuter.py before any write is possible.
"""

import os
import shutil
import stat
from pathlib import Path

from readme_agent.errors import GitSafetyError
from readme_agent.gitsafety._git import run_git
from readme_agent.registry.models import ProductEntry


def force_rmtree(path: Path) -> None:
    """git writes objects read-only; plain shutil.rmtree chokes on that on
    Windows. Clear the read-only bit on access-denied and retry. Public (not
    module-private) since `orchestrator.py::run_registry()` reuses this same
    primitive for post-profile baseline cleanup (decision #40/Part B) rather
    than a fourth duplicate of this exact function. Caller must check
    `path.exists()` first -- `shutil.rmtree` raises if the top-level path is
    already gone, and that's a normal, expected case for callers here."""

    def _on_error(func, target_path, exc_info):
        os.chmod(target_path, stat.S_IWRITE)
        func(target_path)

    shutil.rmtree(path, onerror=_on_error)


def clone_baseline(entry: ProductEntry, baseline_path: Path) -> Path:
    """Fresh, read-only reference clone. Always re-cloned so it reflects the
    current upstream state -- never fetched/reset in place."""
    if baseline_path.exists():
        force_rmtree(baseline_path)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)

    # No explicit --branch: --depth 1 alone clones the HEAD of the remote's
    # default branch, which is exactly what we want without needing a
    # separate preflight lookup baked into the clone call itself.
    result = run_git(
        ["clone", "--depth", "1", entry.clone_url, str(baseline_path)],
        timeout=300,
    )
    if result.returncode != 0:
        raise GitSafetyError(f"baseline clone of {entry.org_repo} failed: {result.stderr}")
    return baseline_path


def create_work_clone(entry: ProductEntry, baseline_path: Path, work_path: Path) -> Path:
    """Fast local-to-local clone from the baseline, then origin is restored to
    the real GitHub URL for realism/evidence (cloning from a local baseline
    path would otherwise leave `origin` pointing at a local path)."""
    if work_path.exists():
        force_rmtree(work_path)
    work_path.parent.mkdir(parents=True, exist_ok=True)

    result = run_git(
        ["clone", "--no-tags", str(baseline_path), str(work_path)],
        timeout=120,
    )
    if result.returncode != 0:
        raise GitSafetyError(f"work clone of {entry.org_repo} failed: {result.stderr}")

    result = run_git(["remote", "set-url", "origin", entry.repo_url + ".git"], cwd=work_path)
    if result.returncode != 0:
        raise GitSafetyError(f"restoring origin URL for {entry.org_repo} failed: {result.stderr}")

    return work_path


def remote_head_sha(clone_url: str, timeout: float = 15) -> str | None:
    """Cheap freshness probe (decision #40/Part B): `git ls-remote` reports
    the remote's default-branch HEAD commit SHA without cloning anything --
    one tiny network round-trip, not the ~1GB+ transfer `clone_baseline()`
    can cost on a large registry repo. `None` on any failure (unreachable
    remote, timeout, unexpected output) -- callers must treat that as "no
    freshness signal available," never as a cache-invalidation error, since
    this is an optimization, not a correctness dependency: falling back to a
    real clone is always safe."""
    try:
        result = run_git(["ls-remote", clone_url, "HEAD"], timeout=timeout)
    except Exception:  # noqa: BLE001 -- a failed probe just means "clone anyway"
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    first_line = result.stdout.strip().splitlines()[0]
    sha = first_line.split()[0] if first_line.split() else ""
    return sha or None


def toplevel_matches(repo_path: Path) -> bool:
    """Safety guard adapted from aspose.org's clone_cache.py: before any
    destructive operation, confirm git will actually operate on repo_path and
    not a parent/wrong repo."""
    result = run_git(["rev-parse", "--show-toplevel"], cwd=repo_path, timeout=5)
    if result.returncode != 0:
        return False
    resolved = Path(result.stdout.strip()).resolve()
    return resolved == repo_path.resolve()
