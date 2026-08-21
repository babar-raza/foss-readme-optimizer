"""Run the offline knowledge-to-README diagnostic across the frozen registry."""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from readme_agent import paths
from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.acceptance_contract import current_fact_acceptance_contract
from readme_agent.facts.knowledge_qualification_models import (
    PortfolioKnowledgeQualificationV1,
    RepositoryKnowledgeQualificationV1,
)
from readme_agent.facts.portfolio_knowledge_selection import PortfolioKnowledgeSelectionV1
from readme_agent.facts.repository_knowledge_generator import (
    current_repository_knowledge_generator_sha256,
)
from readme_agent.facts.repository_knowledge_qualification import qualify_repository_knowledge
from readme_agent.registry.loader import PRODUCTS_PATH, load_products
from readme_agent.repository_snapshot import capture_repository_snapshot


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _typed_disposition(
    entry,
    *,
    detail: str,
    output_dir: Path,
) -> RepositoryKnowledgeQualificationV1:
    result = RepositoryKnowledgeQualificationV1(
        org_repo=entry.org_repo,
        family=entry.family,
        platform=entry.platform,
        source_revision=None,
        status="non_processable_no_implementation",
        detail=detail,
        artifact_root=str(output_dir.resolve()),
    )
    write_redacted_json(output_dir / "result.json", result)
    refresh_sha256sums(output_dir)
    return result


def _baseline_failure(
    entry,
    *,
    detail: str,
    source_revision: str | None,
    output_dir: Path,
) -> RepositoryKnowledgeQualificationV1:
    result = RepositoryKnowledgeQualificationV1(
        org_repo=entry.org_repo,
        family=entry.family,
        platform=entry.platform,
        source_revision=source_revision,
        status="baseline_unavailable",
        detail=detail[:2000],
        artifact_root=str(output_dir.resolve()),
    )
    write_redacted_json(output_dir / "result.json", result)
    refresh_sha256sums(output_dir)
    return result


def _summary_markdown(report: PortfolioKnowledgeQualificationV1) -> str:
    lines = [
        "# Portfolio Knowledge Qualification",
        "",
        "This is an offline, zero-LLM, zero-effect diagnostic. It is not Gate A or independent ",
        "review acceptance.",
        "",
        f"- Registry entries: {report.denominator}",
        f"- Processable entries: {report.processable}",
        f"- Typed non-processable dispositions: {report.typed_dispositions}",
        f"- Candidates generated: {report.candidate_generated}",
        f"- Document-valid candidates: {report.document_valid}",
        f"- Qualified on the current fact contract: {report.qualified_current_contract}",
        f"- Qualified with a stale fact contract: {report.qualified_stale_contract}",
        "- LLM provider calls: 0",
        "- Product effects: 0",
        "",
        "| Repository | Platform | Status | Candidate | Document Valid | Detail |",
        "|---|---|---|---:|---:|---|",
    ]
    for entry in report.entries:
        detail = entry.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {entry.org_repo} | {entry.platform} | `{entry.status}` | "
            f"{'yes' if entry.candidate_generated else 'no'} | "
            f"{'yes' if entry.document_valid else 'no'} | {detail} |"
        )
    return "\n".join(lines) + "\n"


def qualify_portfolio_knowledge(
    selection_receipt: Path,
    *,
    output_root: Path,
) -> PortfolioKnowledgeQualificationV1:
    """Qualify current frozen inputs without recollection, LLMs, or remote effects."""

    selection = PortfolioKnowledgeSelectionV1.model_validate_json(
        selection_receipt.read_text(encoding="utf-8")
    )
    products = {entry.org_repo: entry for entry in load_products()}
    selected = {entry.org_repo: entry for entry in selection.entries}
    if set(products) != set(selected):
        raise ValueError("selection receipt denominator differs from data/products.json")
    generator_sha256 = current_repository_knowledge_generator_sha256()
    if selection.generator_sha256 != generator_sha256:
        raise ValueError("selection receipt generator identity is stale")

    results: list[RepositoryKnowledgeQualificationV1] = []
    for org_repo in sorted(products):
        entry = products[org_repo]
        selection_entry = selected[org_repo]
        revision = selection_entry.source_revision
        revision_dir = revision or "typed-disposition"
        output_dir = output_root / f"{entry.org}__{entry.repo_name}" / revision_dir
        if selection_entry.status == "non_processable_no_implementation":
            results.append(
                _typed_disposition(
                    entry,
                    detail=selection_entry.detail,
                    output_dir=output_dir,
                )
            )
            continue
        if selection_entry.status != "current" or revision is None:
            results.append(
                _baseline_failure(
                    entry,
                    detail=f"knowledge selection is not current: {selection_entry.detail}",
                    source_revision=revision,
                    output_dir=output_dir,
                )
            )
            continue
        baseline = paths.baseline_dir(entry.org, entry.repo_name)
        try:
            snapshot = capture_repository_snapshot(entry, baseline)
        except Exception as exc:  # noqa: BLE001 - isolate one diagnostic repository
            results.append(
                _baseline_failure(
                    entry,
                    detail=f"{type(exc).__name__}: {exc}",
                    source_revision=revision,
                    output_dir=output_dir,
                )
            )
            continue
        results.append(
            qualify_repository_knowledge(
                entry,
                snapshot,
                expected_revision=revision,
                output_dir=output_dir,
            )
        )

    counts = Counter(entry.status for entry in results)
    report = PortfolioKnowledgeQualificationV1(
        generated_at=datetime.now(UTC).isoformat(),
        registry_sha256=_sha256(PRODUCTS_PATH),
        selection_receipt_sha256=_sha256(selection_receipt),
        generator_sha256=generator_sha256,
        fact_acceptance_contract_sha256=current_fact_acceptance_contract().canonical_hash(),
        denominator=len(results),
        processable=sum(entry.status != "non_processable_no_implementation" for entry in results),
        typed_dispositions=counts["non_processable_no_implementation"],
        candidate_generated=sum(entry.candidate_generated for entry in results),
        document_valid=sum(entry.document_valid for entry in results),
        qualified_current_contract=counts["qualified"],
        qualified_stale_contract=counts["qualified_stale_fact_contract"],
        status_counts=dict(sorted(counts.items())),
        entries=tuple(results),
    )
    write_redacted_json(output_root / "portfolio-summary.json", report)
    write_redacted_text(output_root / "portfolio-summary.md", _summary_markdown(report))
    refresh_sha256sums(output_root)
    return report


__all__ = ["qualify_portfolio_knowledge"]
