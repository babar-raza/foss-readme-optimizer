"""Qualify one frozen repository's knowledge through the native README hard gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from readme_agent import paths
from readme_agent.evidence.writer import (
    refresh_sha256sums,
    unified_diff,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.acceptance_contract import current_fact_acceptance_contract
from readme_agent.facts.knowledge_application_evidence import (
    build_knowledge_application_report,
)
from readme_agent.facts.knowledge_qualification_models import (
    QualificationStatus,
    RepositoryKnowledgeQualificationV1,
)
from readme_agent.facts.repository_knowledge_generator import repository_knowledge_data_root
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.runtime_context import load_runtime_link_inputs
from readme_agent.presentation.verified_template_document import (
    build_verified_template_document_candidate,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.document_validation import validate_readme_document_candidate
from readme_agent.readme.verified_preservation_composition import (
    build_offline_knowledge_qualification_plan,
    offline_knowledge_qualification_blockers,
)
from readme_agent.registry.models import ProductEntry
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot
from readme_agent.validation.aspose_check_coverage import build_check_coverage_report
from readme_agent.validation.aspose_checks_bridge import (
    blocking_aspose_check_findings,
    blocking_aspose_check_gaps,
    run_aspose_checks,
)

_CLASSIFICATION_PATH = Path("data/aspose_check_classification.json")


def _failure(
    entry: ProductEntry,
    output_dir: Path,
    status: QualificationStatus,
    detail: str,
    *,
    source_revision: str | None,
    facts_path: Path | None = None,
    facts_hash: str | None = None,
    contract_current: bool | None = None,
) -> RepositoryKnowledgeQualificationV1:
    result = RepositoryKnowledgeQualificationV1(
        org_repo=entry.org_repo,
        family=entry.family,
        platform=entry.platform,
        source_revision=source_revision,
        status=status,
        detail=detail[:2000],
        artifact_root=str(output_dir.resolve()),
        facts_path=str(facts_path.resolve()) if facts_path is not None else None,
        facts_hash=facts_hash,
        fact_acceptance_contract_current=contract_current,
    )
    write_redacted_json(output_dir / "result.json", result)
    refresh_sha256sums(output_dir)
    return result


def _knowledge_counts(report) -> tuple[int, int]:
    rendered = sum(
        disposition.disposition == "rendered_with_exact_spans"
        for disposition in report.final_dispositions
    )
    omitted = sum(
        disposition.disposition == "intentionally_omitted_with_evidence"
        for disposition in report.final_dispositions
    )
    return rendered, omitted


def qualify_repository_knowledge(
    entry: ProductEntry,
    snapshot: RepositorySnapshotV1,
    *,
    expected_revision: str,
    output_dir: Path,
) -> RepositoryKnowledgeQualificationV1:
    """Render and validate without LLM calls, lifecycle transitions, or product effects."""

    if snapshot.source_revision != expected_revision:
        return _failure(
            entry,
            output_dir,
            "baseline_revision_mismatch",
            f"baseline {snapshot.source_revision} differs from selection {expected_revision}",
            source_revision=snapshot.source_revision,
        )
    if snapshot.readme_path is None:
        return _failure(
            entry,
            output_dir,
            "baseline_unavailable",
            "immutable snapshot has no README",
            source_revision=snapshot.source_revision,
        )
    verify_repository_snapshot(snapshot)
    bundle = paths.readme_poc_repository_dir(entry.org, entry.repo_name, snapshot.source_revision)
    facts_path = bundle / "facts" / "product-facts.json"
    manifest_path = bundle / "manifest.json"
    if not facts_path.is_file() or not manifest_path.is_file():
        return _failure(
            entry,
            output_dir,
            "facts_unavailable",
            "current-revision ProductFactsV2 bundle or manifest is missing",
            source_revision=snapshot.source_revision,
            facts_path=facts_path,
        )

    try:
        facts = ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        facts_hash = facts.canonical_hash()
        if facts.org_repo != entry.org_repo or manifest.get("source_revision") != expected_revision:
            raise ValueError("facts identity or manifest revision does not match the snapshot")
        if manifest.get("facts_hash") != facts_hash:
            raise ValueError("persisted facts hash does not match the semantic fact graph")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return _failure(
            entry,
            output_dir,
            "facts_invalid",
            f"{type(exc).__name__}: {exc}",
            source_revision=snapshot.source_revision,
            facts_path=facts_path,
        )

    contract = current_fact_acceptance_contract(entry.ecosystem, entry.family)
    contract_current = manifest.get("fact_acceptance_contract_hash") == contract.canonical_hash()
    source_text = (snapshot.root_path / snapshot.readme_path).read_text(encoding="utf-8")
    assessment = assess_readme_document(
        entry.org_repo,
        source_text,
        facts,
        base_revision=snapshot.source_revision,
    )
    write_redacted_json(
        output_dir / "facts" / "binding.json",
        {
            "facts_path": str(facts_path.resolve()),
            "facts_hash": facts_hash,
            "fact_acceptance_contract_current": contract_current,
            "stored_fact_acceptance_contract_hash": manifest.get("fact_acceptance_contract_hash"),
            "current_fact_acceptance_contract_hash": contract.canonical_hash(),
        },
    )
    write_redacted_json(output_dir / "planning" / "assessment.json", assessment)
    blockers = offline_knowledge_qualification_blockers(
        entry.org_repo,
        source_text,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )
    plan = build_offline_knowledge_qualification_plan(
        entry.org_repo,
        source_text,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )
    if plan is None:
        return _failure(
            entry,
            output_dir,
            "plan_unavailable",
            "zero-provider plan blocked by: " + "; ".join(blockers or ("draft_invalid",)),
            source_revision=snapshot.source_revision,
            facts_path=facts_path,
            facts_hash=facts_hash,
            contract_current=contract_current,
        )
    write_redacted_json(output_dir / "planning" / "composition-plan.json", plan)

    try:
        link_catalogs, link_policy = load_runtime_link_inputs(entry.org_repo)
        candidate, document_plan = build_verified_template_document_candidate(
            facts,
            source_text,
            snapshot.source_revision,
            plan,
            link_catalogs=link_catalogs,
            link_allocation_policy=link_policy,
            repository_root=snapshot.root_path,
        )
        validation = validate_readme_document_candidate(
            source_text,
            candidate,
            document_plan,
            facts,
            link_catalogs=link_catalogs,
        )
        checks = run_aspose_checks(candidate, facts)
        classification = json.loads(_CLASSIFICATION_PATH.read_text(encoding="utf-8"))
        coverage = build_check_coverage_report(checks, classification)
        blocking_findings = blocking_aspose_check_findings(checks)
        blocking_gaps = blocking_aspose_check_gaps(checks)
        application = build_knowledge_application_report(
            entry.org_repo,
            entry.family,
            entry.platform,
            data_root=repository_knowledge_data_root(snapshot),
            clone_cache=snapshot.root_path,
            source_revision=snapshot.source_revision,
            document_plan=document_plan,
            candidate_text=candidate,
            status="final",
            reviewer_disposition="OFFLINE_DETERMINISTIC_QUALIFICATION",
        )
    except Exception as exc:  # noqa: BLE001 - isolate one diagnostic repository
        return _failure(
            entry,
            output_dir,
            "render_failed",
            f"{type(exc).__name__}: {exc}",
            source_revision=snapshot.source_revision,
            facts_path=facts_path,
            facts_hash=facts_hash,
            contract_current=contract_current,
        )

    write_redacted_text(output_dir / "source" / "README.md", source_text)
    write_redacted_json(output_dir / "planning" / "document-plan.json", document_plan)
    write_redacted_text(output_dir / "candidate" / "README.md", candidate)
    write_redacted_text(
        output_dir / "candidate" / "README.patch",
        unified_diff(source_text, candidate),
    )
    write_redacted_json(output_dir / "validation" / "document-validation.json", validation)
    write_redacted_json(output_dir / "validation" / "check-coverage.json", coverage)
    write_redacted_json(output_dir / "validation" / "knowledge-application.json", application)

    rendered, omitted = _knowledge_counts(application)
    accepted = validation.valid and not blocking_findings and not blocking_gaps
    status: QualificationStatus
    if not accepted:
        status = "validation_rejected"
    elif contract_current:
        status = "qualified"
    else:
        status = "qualified_stale_fact_contract"
    result = RepositoryKnowledgeQualificationV1(
        org_repo=entry.org_repo,
        family=entry.family,
        platform=entry.platform,
        source_revision=snapshot.source_revision,
        status=status,
        detail=(
            "native deterministic candidate passed document and blocking checks"
            if accepted
            else "native deterministic candidate failed one or more blocking checks"
        ),
        artifact_root=str(output_dir.resolve()),
        facts_path=str(facts_path.resolve()),
        facts_hash=facts_hash,
        fact_acceptance_contract_current=contract_current,
        candidate_sha256=hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
        candidate_generated=True,
        document_valid=validation.valid,
        check_count=coverage.check_count,
        blocking_finding_count=len(blocking_findings),
        blocking_gap_count=len(blocking_gaps),
        knowledge_considered_count=application.considered_count,
        knowledge_selected_count=application.selected_count,
        knowledge_rendered_count=rendered,
        knowledge_omitted_count=omitted,
    )
    write_redacted_json(output_dir / "result.json", result)
    refresh_sha256sums(output_dir)
    verify_repository_snapshot(snapshot)
    return result


__all__ = ["qualify_repository_knowledge"]
