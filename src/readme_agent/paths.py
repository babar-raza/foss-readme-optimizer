"""Resolution of the disposable, git-ignored runtime directory.

Deliberately cwd-relative (not repo-root-walking) so local dev (run from the
repo root) and a GitHub Actions runner (checkout puts cwd at repo root)
resolve identically with zero path-detection magic.
"""

import os
from pathlib import Path


def runs_dir() -> Path:
    override = os.environ.get("README_AGENT_RUNS_DIR")
    base = Path(override) if override else Path.cwd() / "runs"
    return base


def baseline_dir(org: str, repo: str) -> Path:
    return runs_dir() / "baseline" / f"{org}__{repo}"


def work_dir(org: str, repo: str) -> Path:
    """Deliberately stable across invocations, unlike baseline (always fresh)
    and evidence (always run_id-scoped): since this tool never pushes, the
    *only* place idempotency (a second run finding its own prior marker span
    and skipping the LLM) can live is a persistent local work clone. A fresh
    work clone every run would make "run twice, zero new diff" fictional."""
    return runs_dir() / "work" / f"{org}__{repo}"


def evidence_dir(run_id: str) -> Path:
    return runs_dir() / "evidence" / run_id
