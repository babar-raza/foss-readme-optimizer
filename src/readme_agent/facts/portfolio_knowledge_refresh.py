"""Refresh source-bound repository knowledge for a disjoint allow-listed cohort."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

from readme_agent import paths
from readme_agent.facts.aspose_knowledge_claims import (
    load_bundle_provenance,
    load_knowledge_claims_with_findings,
)
from readme_agent.facts.repository_knowledge_generator import (
    current_repository_knowledge_generator_sha256,
    generate_repository_knowledge,
    repository_knowledge_data_root,
)
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.registry.loader import load_products
from readme_agent.repository_snapshot import capture_repository_snapshot


class PortfolioKnowledgeRefreshEntryV1(BaseModel):
    """Outcome of refreshing one registry member's deterministic knowledge."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str
    family: str
    platform: str
    source_revision: str | None
    status: str
    claim_count: int = 0
    generator_sha256: str
    output_root: str | None = None
    detail: str


class PortfolioKnowledgeRefreshV1(BaseModel):
    """Checksum-ready aggregate for one disjoint refresh cohort."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    generated_at: str
    generator_sha256: str
    requested_repositories: tuple[str, ...]
    entries: tuple[PortfolioKnowledgeRefreshEntryV1, ...]


def refresh_repository_knowledge_cohort(
    repositories: tuple[str, ...],
) -> PortfolioKnowledgeRefreshV1:
    """Refresh one exact cohort without granting generated claims factual authority."""

    products = {entry.org_repo: entry for entry in load_products()}
    unknown = sorted(set(repositories) - set(products))
    if unknown:
        raise ValueError(f"repositories are not in data/products.json: {unknown}")
    generator_sha256 = current_repository_knowledge_generator_sha256()
    results: list[PortfolioKnowledgeRefreshEntryV1] = []
    for org_repo in repositories:
        entry = products[org_repo]
        if entry.family == "psd":
            results.append(
                PortfolioKnowledgeRefreshEntryV1(
                    org_repo=org_repo,
                    family=entry.family,
                    platform=entry.platform,
                    source_revision=None,
                    status="non_processable_no_implementation",
                    generator_sha256=generator_sha256,
                    detail=(
                        "source-empty PSD repository; refresh resumes when implementation exists"
                    ),
                )
            )
            continue
        try:
            baseline = clone_baseline(entry, paths.baseline_dir(entry.org, entry.repo_name))
            snapshot = capture_repository_snapshot(entry, baseline)
            data_root = repository_knowledge_data_root(snapshot)
            output_root = data_root / "knowledge" / entry.family / entry.platform / "merged"
            generation = generate_repository_knowledge(
                snapshot,
                family=entry.family,
                platform=entry.platform,
                output_root=output_root,
            )
            if generation.status == "unavailable":
                raise ValueError(generation.detail)
            loaded = load_knowledge_claims_with_findings(
                entry.family,
                entry.platform,
                data_root=data_root,
            )
            provenance = load_bundle_provenance(
                entry.family,
                entry.platform,
                data_root=data_root,
            )
            if provenance is None or provenance.repo_sha != snapshot.source_revision:
                raise ValueError("generated bundle provenance does not match immutable source")
            if loaded.findings:
                raise ValueError(f"generated bundle has {len(loaded.findings)} load finding(s)")
            if not loaded.claims:
                raise ValueError("generated bundle has zero claims")
            claim_ids = [claim.global_claim_id for claim in loaded.claims]
            if len(claim_ids) != len(set(claim_ids)):
                raise ValueError("generated bundle contains duplicate global claim ids")
            results.append(
                PortfolioKnowledgeRefreshEntryV1(
                    org_repo=org_repo,
                    family=entry.family,
                    platform=entry.platform,
                    source_revision=snapshot.source_revision,
                    status="current",
                    claim_count=len(loaded.claims),
                    generator_sha256=generation.generator_sha256 or generator_sha256,
                    output_root=str(data_root.resolve()),
                    detail=generation.detail,
                )
            )
        except Exception as exc:  # noqa: BLE001 -- isolate one repository from its cohort
            results.append(
                PortfolioKnowledgeRefreshEntryV1(
                    org_repo=org_repo,
                    family=entry.family,
                    platform=entry.platform,
                    source_revision=None,
                    status="failed",
                    generator_sha256=generator_sha256,
                    detail=f"{type(exc).__name__}: {exc}"[:2000],
                )
            )
    return PortfolioKnowledgeRefreshV1(
        generated_at=datetime.now(UTC).isoformat(),
        generator_sha256=generator_sha256,
        requested_repositories=repositories,
        entries=tuple(results),
    )
