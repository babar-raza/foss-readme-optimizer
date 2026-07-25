"""Materialize revision-addressed local-POC snapshot evidence."""

from __future__ import annotations

from pathlib import Path

from readme_agent import paths
from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.schema_v2 import ProductFactsV2
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


def write_local_poc_product_facts(
    snapshot: RepositorySnapshotV1,
    facts: ProductFactsV2,
    *,
    findings: list[dict],
    resolution_source: str,
    proposed_product_truth: dict | None = None,
    lifecycle_status: str = "FACTS_READY",
    prompt_hash: str | None = None,
) -> Path:
    """Persist the fact graph and its inspectable provenance projections."""
    org, repo = snapshot.org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, snapshot.source_revision)
    facts_dir = bundle_dir / "facts"
    write_redacted_json(facts_dir / "product-facts.json", facts)
    write_redacted_json(
        facts_dir / "provenance.json",
        {
            fact.fact_id: {
                "field": fact.field,
                "source": fact.source.model_dump(mode="json"),
                "verification_state": fact.verification_state,
                "confidence": fact.confidence,
                "authoritative_owner": fact.authoritative_owner,
                "affected_surfaces": fact.affected_surfaces,
            }
            for fact in facts.facts
        },
    )
    write_redacted_json(
        facts_dir / "conflicts.json",
        {
            fact.fact_id: [conflict.model_dump(mode="json") for conflict in fact.conflicts]
            for fact in facts.facts
            if fact.conflicts
        },
    )
    write_redacted_json(
        facts_dir / "acquisition.json",
        {
            "coordinates": facts.selected_fact("installation.coordinates").model_dump(mode="json"),
            "verified_acquisition": facts.selected_fact(
                "installation.verified_acquisition"
            ).model_dump(mode="json"),
            "minimal_example": facts.selected_fact("example.minimal").model_dump(mode="json"),
        },
    )
    write_redacted_json(facts_dir / "findings.json", findings)
    if proposed_product_truth is not None:
        write_redacted_json(facts_dir / "proposed-product-truth.json", proposed_product_truth)
    write_redacted_json(
        bundle_dir / "manifest.json",
        {
            "schema_version": 1,
            "org_repo": snapshot.org_repo,
            "source_revision": snapshot.source_revision,
            "lifecycle_status": lifecycle_status,
            "facts_hash": facts.canonical_hash(),
            "resolution_source": resolution_source,
            "prompt_hash": prompt_hash,
            "complete": False,
            "completed_stages": ["SNAPSHOTTED", "PROFILED", lifecycle_status],
        },
    )
    refresh_sha256sums(bundle_dir)
    return bundle_dir
