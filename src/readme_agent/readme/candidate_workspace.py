"""Prepare and fingerprint the push-disabled README candidate workspace."""

import hashlib
import json
from pathlib import Path

from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import create_work_clone
from readme_agent.registry.models import PolicyProfile, ProductEntry


def policy_content_hash(policy: PolicyProfile) -> str:
    canonical = json.dumps(policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def work_clone_fingerprint_sidecar(work_path: Path) -> Path:
    return work_path.parent / f"{work_path.name}.tracked-content-fingerprint"


def is_valid_work_clone(work_path: Path) -> bool:
    """Require git to resolve the exact workspace, never a parent repository."""

    result = run_git(["rev-parse", "--show-toplevel"], cwd=work_path)
    if result.returncode != 0:
        return False
    try:
        resolved = Path(result.stdout.strip()).resolve()
    except OSError:
        return False
    return resolved == work_path.resolve()


def ensure_work_clone(
    entry: ProductEntry,
    baseline_path: Path,
    work_path: Path,
    *,
    fresh_fingerprint: str,
) -> Path:
    """Reuse only a valid workspace built from identical tracked content."""

    sidecar = work_clone_fingerprint_sidecar(work_path)
    if work_path.exists() and (work_path / ".git").exists() and is_valid_work_clone(work_path):
        if sidecar.exists() and sidecar.read_text(encoding="utf-8").strip() == fresh_fingerprint:
            return work_path
    result = create_work_clone(entry, baseline_path, work_path)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(fresh_fingerprint, encoding="utf-8")
    return result
