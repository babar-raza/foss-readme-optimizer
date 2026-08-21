"""Audit current generated knowledge through the repository-corroborating selector."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from readme_agent import paths
from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.facts.aspose_knowledge_selection import select_knowledge_claims
from readme_agent.facts.portfolio_knowledge_refresh import PortfolioKnowledgeRefreshV1
from readme_agent.registry.loader import load_products
from readme_agent.repository_snapshot import capture_repository_snapshot


class PortfolioKnowledgeSelectionEntryV1(BaseModel):
    """Aggregate selection accountability for one registry repository."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str
    family: str
    platform: str
    source_revision: str | None
    status: str
    claim_count: int = 0
    disposition_count: int = 0
    selected_count: int = 0
    rejected_count: int = 0
    freshness: str | None = None
    selected_fields: dict[str, int] = Field(default_factory=dict)
    selected_kinds: dict[str, int] = Field(default_factory=dict)
    rejection_reasons: dict[str, int] = Field(default_factory=dict)
    selection_path: str | None = None
    detail: str


class PortfolioKnowledgeSelectionV1(BaseModel):
    """Portfolio matrix proving every generated claim received one selector outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    generator_sha256: str
    denominator: int
    processable: int
    typed_dispositions: int
    failed: int
    total_claims: int
    total_selected: int
    entries: tuple[PortfolioKnowledgeSelectionEntryV1, ...]


def _load_refresh_entries(receipts: tuple[Path, ...]) -> tuple[str, dict[str, dict]]:
    entries: dict[str, dict] = {}
    generator_ids: set[str] = set()
    for receipt in receipts:
        report = PortfolioKnowledgeRefreshV1.model_validate_json(
            receipt.read_text(encoding="utf-8")
        )
        generator_ids.add(report.generator_sha256)
        for entry in report.entries:
            if entry.org_repo in entries:
                raise ValueError(f"duplicate refresh entry: {entry.org_repo}")
            entries[entry.org_repo] = entry.model_dump(mode="json")
    if len(generator_ids) != 1:
        raise ValueError("refresh receipts do not share one generator identity")
    return next(iter(generator_ids)), entries


def audit_portfolio_knowledge_selection(
    refresh_receipts: tuple[Path, ...],
    *,
    output_dir: Path,
) -> PortfolioKnowledgeSelectionV1:
    """Select and disposition every current claim without composing README bytes."""

    generator_sha256, refreshed = _load_refresh_entries(refresh_receipts)
    products = {entry.org_repo: entry for entry in load_products()}
    if set(refreshed) != set(products):
        missing = sorted(set(products) - set(refreshed))
        extra = sorted(set(refreshed) - set(products))
        raise ValueError(f"refresh denominator mismatch: missing={missing}, extra={extra}")

    results: list[PortfolioKnowledgeSelectionEntryV1] = []
    for org_repo, entry in products.items():
        refresh = refreshed[org_repo]
        if refresh["status"] == "non_processable_no_implementation":
            results.append(
                PortfolioKnowledgeSelectionEntryV1(
                    org_repo=org_repo,
                    family=entry.family,
                    platform=entry.platform,
                    source_revision=None,
                    status=refresh["status"],
                    detail=refresh["detail"],
                )
            )
            continue
        if refresh["status"] != "current" or not refresh["source_revision"]:
            results.append(
                PortfolioKnowledgeSelectionEntryV1(
                    org_repo=org_repo,
                    family=entry.family,
                    platform=entry.platform,
                    source_revision=refresh["source_revision"],
                    status="failed",
                    detail=f"knowledge refresh is not current: {refresh['detail']}",
                )
            )
            continue

        baseline = paths.baseline_dir(entry.org, entry.repo_name)
        snapshot = capture_repository_snapshot(entry, baseline)
        if snapshot.source_revision != refresh["source_revision"]:
            raise ValueError(f"baseline drifted after refresh: {org_repo}")
        selection = select_knowledge_claims(
            entry.family,
            entry.platform,
            data_root=Path(refresh["output_root"]),
            clone_cache=baseline,
            source_revision=snapshot.source_revision,
        )
        if selection.load_findings:
            raise ValueError(f"selector load findings for {org_repo}: {selection.load_findings}")
        if len(selection.dispositions) != refresh["claim_count"]:
            raise ValueError(f"selector accountability mismatch for {org_repo}")

        repository_alias = org_repo.replace("/", "__")
        selection_path = output_dir / "repositories" / repository_alias / "selection.json"
        write_redacted_json(selection_path, selection)
        refresh_sha256sums(selection_path.parent)
        selected = [item for item in selection.dispositions if item.accepted]
        results.append(
            PortfolioKnowledgeSelectionEntryV1(
                org_repo=org_repo,
                family=entry.family,
                platform=entry.platform,
                source_revision=snapshot.source_revision,
                status="current",
                claim_count=refresh["claim_count"],
                disposition_count=len(selection.dispositions),
                selected_count=len(selected),
                rejected_count=len(selection.dispositions) - len(selected),
                freshness=selection.freshness,
                selected_fields=dict(
                    Counter(
                        item.resulting_fact_field
                        for item in selected
                        if item.resulting_fact_field is not None
                    )
                ),
                selected_kinds=dict(Counter(item.kind for item in selected)),
                rejection_reasons=dict(
                    Counter(item.rejection_reason or "accepted" for item in selection.dispositions)
                ),
                selection_path=str(selection_path.resolve()),
                detail="every generated claim received one current-source selection disposition",
            )
        )

    return PortfolioKnowledgeSelectionV1(
        generator_sha256=generator_sha256,
        denominator=len(results),
        processable=sum(entry.status == "current" for entry in results),
        typed_dispositions=sum(
            entry.status == "non_processable_no_implementation" for entry in results
        ),
        failed=sum(entry.status == "failed" for entry in results),
        total_claims=sum(entry.claim_count for entry in results),
        total_selected=sum(entry.selected_count for entry in results),
        entries=tuple(results),
    )
