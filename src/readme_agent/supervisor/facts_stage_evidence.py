"""Recover the immutable snapshot bound to a completed product-truth stage."""

from __future__ import annotations

from readme_agent import paths
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2


def load_facts_stage_snapshot(
    org_repo: str,
    lifecycle: ReadmePocLifecycleStateV2 | None,
) -> RepositorySnapshotV1:
    """Load the exact captured snapshot named by durable product-truth state."""

    if lifecycle is None:
        raise RuntimeError("facts-stage evidence requires a durable README lifecycle")
    if lifecycle.content_assurance != "repository_verified":
        raise RuntimeError("facts-stage evidence requires repository-verified assurance")
    if lifecycle.source_revision is None:
        raise RuntimeError("facts-stage lifecycle is missing its source revision")

    try:
        org, repo = org_repo.split("/", maxsplit=1)
        if not org or not repo or "/" in repo:
            raise ValueError
    except ValueError as exc:
        raise RuntimeError(f"invalid facts-stage repository identity: {org_repo!r}") from exc

    revision_path = (
        paths.readme_poc_repository_dir(org, repo, lifecycle.source_revision)
        / "source"
        / "revision.json"
    )
    if not revision_path.is_file():
        raise RuntimeError(f"facts-stage snapshot evidence is missing: {revision_path}")
    try:
        snapshot = RepositorySnapshotV1.model_validate_json(
            revision_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"facts-stage snapshot evidence is invalid: {revision_path}") from exc
    if snapshot.org_repo != org_repo:
        raise RuntimeError(
            "facts-stage snapshot repository mismatch: "
            f"expected {org_repo}, found {snapshot.org_repo}"
        )
    if snapshot.source_revision != lifecycle.source_revision:
        raise RuntimeError(
            "facts-stage snapshot revision mismatch: "
            f"expected {lifecycle.source_revision}, found {snapshot.source_revision}"
        )
    return snapshot
