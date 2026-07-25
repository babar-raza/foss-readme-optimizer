"""Materialize revision-addressed local-POC snapshot evidence."""

from __future__ import annotations

from pathlib import Path

from readme_agent import paths
from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1


def write_local_poc_snapshot(snapshot: RepositorySnapshotV1) -> Path:
    """Write the immutable source portion of one local-POC bundle idempotently.

    This deliberately records only the boundary actually reached.  Facts,
    plans, candidates, reviews, and the final manifest are owned by their
    later stages; writing placeholders for them would make an incomplete run
    look presentation-ready.
    """
    org, repo = snapshot.org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, snapshot.source_revision)
    source_dir = bundle_dir / "source"
    write_redacted_json(source_dir / "revision.json", snapshot)
    write_redacted_json(
        source_dir / "repository-profile.json",
        {
            "org_repo": snapshot.org_repo,
            "inventory_sha256": snapshot.inventory_sha256,
            "package_roots": [root.model_dump(mode="json") for root in snapshot.package_roots],
        },
    )
    if snapshot.readme_path is None:
        write_redacted_json(
            source_dir / "readme-absence.json",
            {"reason": "README absent at immutable source revision"},
        )
    else:
        readme = snapshot.root_path / snapshot.readme_path
        write_redacted_text(source_dir / "README.md", readme.read_text(encoding="utf-8"))
    write_redacted_json(
        bundle_dir / "manifest.json",
        {
            "schema_version": 1,
            "org_repo": snapshot.org_repo,
            "source_revision": snapshot.source_revision,
            "lifecycle_status": "SNAPSHOTTED",
            "complete": False,
            "completed_stages": ["SNAPSHOTTED"],
        },
    )
    refresh_sha256sums(bundle_dir)
    return bundle_dir


def mark_local_poc_profiled(snapshot: RepositorySnapshotV1, bundle_dir: Path) -> None:
    """Advance the bundle manifest after the durable profile transition."""
    write_redacted_json(
        bundle_dir / "manifest.json",
        {
            "schema_version": 1,
            "org_repo": snapshot.org_repo,
            "source_revision": snapshot.source_revision,
            "lifecycle_status": "PROFILED",
            "complete": False,
            "completed_stages": ["SNAPSHOTTED", "PROFILED"],
        },
    )
    refresh_sha256sums(bundle_dir)
