"""Materialize revision-addressed local-POC fact and candidate evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from readme_agent import paths
from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.knowledge_application_evidence import KnowledgeApplicationV1
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm import prompt_registry
from readme_agent.presentation.candidate_benchmark_comparison import (
    build_candidate_benchmark_comparison,
)
from readme_agent.readme.agentic_composition import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.claim_map import ReadmeClaimMapV1
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
from readme_agent.readme.markers import find_presentation_span
from readme_agent.readme.readme_reconciliation import build_readme_reconciliation_report
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.specialists.bounded_review_evidence import (
    build_candidate_bounded_review_evidence,
)
from readme_agent.state.readme_poc_lifecycle import candidate_generation_origin_hash
from readme_agent.supervisor.candidate_llm_accounting import (
    write_candidate_transaction_llm_accounting,
)
from readme_agent.supervisor.local_poc_snapshot_evidence import (
    load_existing_local_poc_manifest,
    write_local_poc_manifest,
)
from readme_agent.supervisor.local_poc_snapshot_evidence import (
    mark_local_poc_profiled as mark_local_poc_profiled,
)
from readme_agent.supervisor.local_poc_snapshot_evidence import (
    write_local_poc_snapshot as write_local_poc_snapshot,
)
from readme_agent.supervisor.local_poc_superseded import archive_and_prune_downstream_artifacts
from readme_agent.supervisor.stage_dependencies import (
    current_candidate_stage_dependency_manifest,
)
from readme_agent.validation.aspose_check_coverage import build_check_coverage_report
from readme_agent.validation.aspose_checks_bridge import run_aspose_checks


def _current_product_truth_policy_hash(org_repo: str) -> str | None:
    """The product_truth policy content these facts were collected under.

    Bound into the facts manifest so `cached_verified_product_truth()` can
    refuse a bundle collected under a different (or absent) `product_truth:`
    block -- see `facts/policy_evidence.py::product_truth_policy_hash`.
    Unlisted repositories degrade to None rather than failing the write.
    """

    from readme_agent.errors import NotAllowlistedError
    from readme_agent.facts.policy_evidence import product_truth_policy_hash
    from readme_agent.registry.loader import require_listed

    try:
        entry = require_listed(org_repo)
    except NotAllowlistedError:
        return None
    return product_truth_policy_hash(getattr(entry, "policy_profile", None))


def write_local_poc_product_facts(
    snapshot: RepositorySnapshotV1,
    facts: ProductFactsV2,
    *,
    findings: list[dict],
    resolution_source: str,
    proposed_product_truth: dict | None = None,
    lifecycle_status: str = "FACTS_READY",
    prompt_hash: str | None = None,
    local_verification_contract_hash: str,
    fact_acceptance_contract_hash: str,
    fact_acceptance_component_hashes: dict[str, str],
) -> Path:
    """Persist the fact graph and its inspectable provenance projections."""
    org, repo = snapshot.org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, snapshot.source_revision)
    facts_dir = bundle_dir / "facts"
    facts_hash = facts.canonical_hash()
    prior_manifest = load_existing_local_poc_manifest(bundle_dir, snapshot.source_revision)
    downstream_reusable = bool(
        prior_manifest.get("candidate_hash")
        and prior_manifest.get("facts_hash") == facts_hash
        and prior_manifest.get("prompt_hash") == prompt_hash
        and prior_manifest.get("local_verification_contract_hash")
        == local_verification_contract_hash
        and prior_manifest.get("fact_acceptance_contract_hash") == fact_acceptance_contract_hash
        and prior_manifest.get("fact_acceptance_component_hashes")
        == fact_acceptance_component_hashes
    )
    if not downstream_reusable:
        archive_and_prune_downstream_artifacts(
            bundle_dir,
            prior_manifest,
            reason="product fact or fact-acceptance dependency changed",
        )

    proposal_path = facts_dir / "proposed-product-truth.json"
    if proposed_product_truth is None:
        proposal_path.unlink(missing_ok=True)
    facts_path = facts_dir / "product-facts.json"
    write_redacted_json(facts_path, facts)
    persisted_facts = ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8"))
    if persisted_facts.canonical_hash() != facts_hash:
        raise RuntimeError(
            "redaction changed the semantic product-facts graph; refusing to seal "
            "an internally inconsistent evidence bundle"
        )
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
        write_redacted_json(proposal_path, proposed_product_truth)
    if downstream_reusable:
        refresh_sha256sums(bundle_dir)
        return bundle_dir
    write_local_poc_manifest(
        bundle_dir,
        {
            "schema_version": 1,
            "org_repo": snapshot.org_repo,
            "source_revision": snapshot.source_revision,
            "lifecycle_status": lifecycle_status,
            "facts_hash": facts_hash,
            "resolution_source": resolution_source,
            "prompt_hash": prompt_hash,
            "local_verification_contract_hash": local_verification_contract_hash,
            "product_truth_policy_hash": _current_product_truth_policy_hash(snapshot.org_repo),
            "fact_acceptance_contract_hash": fact_acceptance_contract_hash,
            "fact_acceptance_component_hashes": fact_acceptance_component_hashes,
            "complete": False,
            "completed_stages": ["SNAPSHOTTED", "PROFILED", lifecycle_status],
        },
    )
    refresh_sha256sums(bundle_dir)
    return bundle_dir


def write_local_poc_knowledge_application(
    snapshot: RepositorySnapshotV1,
    report: KnowledgeApplicationV1,
) -> Path:
    """Persist `knowledge-application.json`: the auditable record of exactly
    which imported aspose.org knowledge claims were considered, selected, or
    rejected (and why) for this repository/revision, and which fact fields
    and candidate sections they influenced. Governance-facing evidence, not
    a runtime input -- see `facts/knowledge_application_evidence.py`."""

    org, repo = snapshot.org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, snapshot.source_revision)
    write_redacted_json(bundle_dir / "knowledge-application.json", report)
    refresh_sha256sums(bundle_dir)
    return bundle_dir


def write_local_poc_trusted_readme_facts(
    snapshot: RepositorySnapshotV1,
    fact_graph: TrustedReadmeFactGraphV1,
) -> Path:
    """Persist trusted facts in an assurance-specific root without replacing verified proof."""

    if fact_graph.org_repo != snapshot.org_repo:
        raise ValueError("trusted fact graph belongs to a different repository")
    if fact_graph.source_revision != snapshot.source_revision:
        raise ValueError("trusted fact graph revision differs from the immutable snapshot")
    if fact_graph.readme_sha256 != snapshot.readme_sha256:
        raise ValueError("trusted fact graph README checksum differs from the immutable snapshot")
    org, repo = snapshot.org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, snapshot.source_revision)
    trusted_dir = bundle_dir / "assurance" / "trusted_inherited"
    facts_dir = trusted_dir / "facts"
    inherited_facts_path = facts_dir / "readme-inherited-facts.json"
    write_redacted_json(inherited_facts_path, fact_graph)
    persisted_graph = TrustedReadmeFactGraphV1.model_validate_json(
        inherited_facts_path.read_text(encoding="utf-8")
    )
    if persisted_graph.canonical_hash() != fact_graph.canonical_hash():
        raise ValueError(
            "trusted fact evidence changed during redaction and cannot retain source accountability"
        )
    write_redacted_json(
        facts_dir / "source-to-fact-map.json",
        {
            fact.fact_id: {
                "material_kind": fact.material_kind,
                "heading_path": list(fact.heading_path),
                "provenance": fact.provenance,
                "source_span": fact.source_span.model_dump(mode="json"),
                "instruction_risks": list(fact.instruction_risks),
            }
            for fact in fact_graph.inherited_facts
        },
    )
    write_redacted_json(
        facts_dir / "configured-standards.json",
        [standard.model_dump(mode="json") for standard in fact_graph.configured_standards],
    )
    graph_hash = fact_graph.canonical_hash()
    write_local_poc_manifest(
        trusted_dir,
        {
            "schema_version": 1,
            "org_repo": snapshot.org_repo,
            "source_revision": snapshot.source_revision,
            "source_bundle": str(bundle_dir / "source"),
            "readme_sha256": snapshot.readme_sha256,
            "lifecycle_status": "TRUSTED_FACTS_EXTRACTED",
            "facts_hash": graph_hash,
            "complete": False,
            "completed_stages": [
                "SNAPSHOTTED",
                "PROFILED",
                "TRUSTED_FACTS_EXTRACTING",
                "TRUSTED_FACTS_EXTRACTED",
            ],
        },
        content_assurance="trusted_inherited",
    )
    refresh_sha256sums(trusted_dir)
    return trusted_dir


def bind_local_poc_fact_acceptance(
    bundle_dir: Path,
    *,
    source_revision: str,
    contract_hash: str,
    component_hashes: dict[str, str],
) -> None:
    """Attach the current contract to a still-valid later-stage manifest."""

    manifest = load_existing_local_poc_manifest(bundle_dir, source_revision)
    if not manifest:
        raise RuntimeError(
            f"cannot bind fact acceptance without a matching manifest at {bundle_dir}"
        )
    if (
        manifest.get("fact_acceptance_contract_hash") == contract_hash
        and manifest.get("fact_acceptance_component_hashes") == component_hashes
    ):
        return
    write_local_poc_manifest(
        bundle_dir,
        {
            **manifest,
            "fact_acceptance_contract_hash": contract_hash,
            "fact_acceptance_component_hashes": component_hashes,
        },
    )
    refresh_sha256sums(bundle_dir)


def reclassify_local_poc_fact_acceptance(
    bundle_dir: Path,
    *,
    source_revision: str,
    lifecycle_status: str,
    contract_hash: str,
    component_hashes: dict[str, str],
) -> None:
    """Reopen a stale later manifest at its current blocked fact boundary."""

    manifest = load_existing_local_poc_manifest(bundle_dir, source_revision)
    if not manifest:
        raise RuntimeError(
            f"cannot reclassify fact acceptance without a matching manifest at {bundle_dir}"
        )
    manifest = archive_and_prune_downstream_artifacts(
        bundle_dir,
        manifest,
        reason="fact acceptance reclassified below README assessment",
    )
    invalidated_keys = {
        "assessment_hash",
        "presentation_plan_hash",
        "agentic_composition_plan_hash",
        "candidate_hash",
        "reviewer_standard_hash",
        "complete",
    }
    retained = {key: value for key, value in manifest.items() if key not in invalidated_keys}
    write_local_poc_manifest(
        bundle_dir,
        {
            **retained,
            "lifecycle_status": lifecycle_status,
            "fact_acceptance_contract_hash": contract_hash,
            "fact_acceptance_component_hashes": component_hashes,
            "complete": False,
            "completed_stages": ["SNAPSHOTTED", "PROFILED", lifecycle_status],
        },
    )
    refresh_sha256sums(bundle_dir)


def _canonical_hash(value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _candidate_product_facts(
    snapshot: RepositorySnapshotV1,
    render_result: dict,
) -> ProductFactsV2:
    """Use the typed facts already consumed by rendering, even in private attempts."""

    supplied = render_result.get("product_facts_v2")
    if isinstance(supplied, dict):
        return ProductFactsV2.model_validate(supplied)
    org, repo = snapshot.org_repo.split("/", maxsplit=1)
    canonical_bundle = paths.readme_poc_repository_dir(org, repo, snapshot.source_revision)
    facts_path = canonical_bundle / "facts" / "product-facts.json"
    if not facts_path.is_file():
        raise ValueError("candidate boundary requires the persisted ProductFactsV2 graph")
    return ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8"))


def _readme_reconciliation_report(
    render_result: dict,
    document_plan: ReadmeDocumentPlanV1,
    snapshot: RepositorySnapshotV1,
) -> dict:
    """Build the mandatory complete source-accountability report."""

    raw_source = render_result.get("source_text")
    if isinstance(raw_source, str):
        source_text = raw_source
    elif snapshot.readme_path is not None:
        source_text = (snapshot.root_path / snapshot.readme_path).read_text(encoding="utf-8")
    else:
        raise ValueError("candidate boundary requires immutable source README text")
    existing = find_presentation_span(source_text)
    inner_text = existing.content if existing is not None else source_text
    report = build_readme_reconciliation_report(document_plan, source_text=inner_text)
    return report.model_dump(mode="json")


def _knowledge_application_report_or_error(render_result: dict) -> dict:
    """Best-effort, final `knowledge-application.json` evidence for this
    render: `idea_candidate.py::prepare_idea_fidelity_candidate` already
    computed the real, post-render K3 report (real `document_plan` +
    rendered candidate bytes in scope together); this degrades to an
    explicit error record rather than ever blocking real candidate
    persistence if that key is somehow absent or fails re-validation.
    Written to the exact same path `product_truth.py`'s pre-render
    `status="provisional"` write already used -- this later, `status="final"`
    write supersedes it, matching `write_redacted_json`'s existing
    overwrite semantics (last write wins)."""

    raw = render_result.get("knowledge_application")
    if not isinstance(raw, dict):
        return {
            "schema_version": 4,
            "error": "no post-render knowledge_application in render_result",
        }
    try:
        KnowledgeApplicationV1.model_validate(raw)
    except ValueError as exc:
        return {"schema_version": 4, "error": str(exc)}
    return raw


_CLASSIFICATION_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "aspose_check_classification.json"
)


def _check_coverage_report_or_error(
    candidate_text: str,
    bundle_dir: Path,
    *,
    facts: ProductFactsV2 | None = None,
) -> dict:
    """Best-effort `check-coverage.json` evidence: every one of the 89+
    vendored checks' real run/pass/fail/skip/error outcome for this exact
    candidate (Gate R7) -- degrades to an explicit error record rather than
    ever blocking real candidate persistence. `facts/product-facts.json`
    is read back from this same bundle (written earlier in this run by
    `write_local_poc_product_facts`) rather than threaded as a new
    parameter, since it is already the real, governed facts this candidate
    was built from."""

    try:
        if facts is None:
            facts_path = bundle_dir / "facts" / "product-facts.json"
            facts = (
                ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8"))
                if facts_path.is_file()
                else None
            )
        classification = json.loads(_CLASSIFICATION_PATH.read_text(encoding="utf-8"))
        result = run_aspose_checks(candidate_text, facts)
        report = build_check_coverage_report(result, classification)
    except (OSError, ValueError) as exc:
        return {"schema_version": 1, "error": str(exc)}
    return report.model_dump(mode="json")


def write_local_poc_readme_candidate(
    snapshot: RepositorySnapshotV1,
    render_result: dict,
    presentation_plan: dict,
    *,
    bundle_dir_override: Path | None = None,
    candidate_role: Literal["initial", "repair"] = "initial",
    include_runtime_accounting: bool = True,
) -> tuple[Path, str, str, str]:
    """Materialize candidate artifacts in a compatibility or private attempt root."""

    if render_result.get("source_revision") != snapshot.source_revision:
        raise ValueError("README candidate revision does not match the immutable snapshot")
    assessment = ReadmeAssessmentV1.model_validate(presentation_plan["readme_assessment"])
    raw_agentic_plan = render_result.get("agentic_composition_plan") or {}
    agentic_plan = (
        ReadmeAgenticCompositionPlanV1.model_validate(raw_agentic_plan)
        if raw_agentic_plan
        else None
    )
    document_plan = ReadmeDocumentPlanV1.model_validate(presentation_plan["readme_document_plan"])
    claim_map = ReadmeClaimMapV1.model_validate(presentation_plan["claim_map"])
    candidate_text = str(render_result["final_text"])
    candidate_hash = hashlib.sha256(candidate_text.encode("utf-8")).hexdigest()
    if (
        candidate_hash != document_plan.candidate_sha256
        or candidate_hash != claim_map.candidate_sha256
    ):
        raise ValueError("README candidate hash disagrees with its document plan or claim map")
    if (
        assessment.facts_hash != document_plan.facts_hash
        or claim_map.facts_hash != document_plan.facts_hash
    ):
        raise ValueError(
            "README assessment, document plan, and claim map use different fact graphs"
        )

    org, repo = snapshot.org_repo.split("/", maxsplit=1)
    bundle_dir = bundle_dir_override or paths.readme_poc_repository_dir(
        org,
        repo,
        snapshot.source_revision,
    )
    assessment_dir = bundle_dir / "assessment"
    planning_dir = bundle_dir / "planning"
    candidate_dir = bundle_dir / "candidate"
    review_dir = bundle_dir / "review"
    patch_text = str(presentation_plan.get("git_patch_proof", {}).get("patch") or "")
    reconciliation_report = _readme_reconciliation_report(render_result, document_plan, snapshot)
    persisted_facts = _candidate_product_facts(snapshot, render_result)
    if persisted_facts.canonical_hash() != document_plan.facts_hash:
        raise ValueError("candidate boundary facts disagree with the document plan")
    bounded_plan, bounded_coverage, bounded_validation = build_candidate_bounded_review_evidence(
        candidate_text=candidate_text,
        document_plan=document_plan,
        product_facts=persisted_facts,
        factual_prompt_sha256=prompt_registry.prompt_hash("factual_readme_plan_review"),
        visitor_prompt_sha256=prompt_registry.prompt_hash("blind_readme_quality_review"),
    )

    write_redacted_json(
        assessment_dir / "current-readme-assessment.json",
        assessment.model_dump(mode="json"),
    )
    write_redacted_json(
        assessment_dir / "evidence-map.json",
        {
            "source_sha256": assessment.source_sha256,
            "facts_hash": assessment.facts_hash,
            "sections": [
                {
                    "section_id": section.section_id,
                    "disposition": section.disposition,
                    "fact_ids": section.fact_ids,
                    "protected_fragment_ids": section.protected_fragment_ids,
                    "evidence": section.evidence,
                }
                for section in assessment.sections
            ],
            "material_claims": [
                claim.model_dump(mode="json") for claim in assessment.material_claims
            ],
        },
    )
    write_redacted_json(
        planning_dir / "presentation-plan.json",
        presentation_plan.get("presentation_plan") or {},
    )
    write_redacted_json(
        planning_dir / "readme-document-plan.json",
        document_plan.model_dump(mode="json"),
    )
    write_redacted_json(
        planning_dir / "agentic-composition-plan.json",
        agentic_plan.model_dump(mode="json") if agentic_plan is not None else {},
    )
    write_redacted_json(
        planning_dir / "selected-capabilities.json",
        {
            "capabilities": [
                "render_readme_candidate",
                "build_presentation_plan",
            ],
            "selection_authority": "canonical readme_presentation specialist",
        },
    )
    write_redacted_json(
        planning_dir / "decision-summary.json",
        {
            "executable": presentation_plan.get("executable") is True,
            "operation_ids": [operation.operation_id for operation in document_plan.operations],
            "section_dispositions": {
                section.section_id: section.disposition for section in assessment.sections
            },
        },
    )
    candidate_component_manifest = current_candidate_stage_dependency_manifest(
        repository=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem=(snapshot.package_roots[0].ecosystem if snapshot.package_roots else "unknown"),
    )
    write_redacted_json(
        planning_dir / "presentation-component-manifest.json",
        candidate_component_manifest.model_dump(mode="json"),
    )
    write_redacted_text(candidate_dir / "README.md", candidate_text)
    write_redacted_text(candidate_dir / "README.patch", patch_text)
    write_redacted_json(candidate_dir / "claim-map.json", claim_map.model_dump(mode="json"))
    write_redacted_text(candidate_dir / "candidate-hash.txt", candidate_hash + "\n")
    write_redacted_json(
        candidate_dir / "readme-reconciliation.json",
        reconciliation_report,
    )
    write_redacted_json(
        candidate_dir / "check-coverage.json",
        _check_coverage_report_or_error(candidate_text, bundle_dir, facts=persisted_facts),
    )
    write_redacted_json(
        bundle_dir / "knowledge-application.json",
        _knowledge_application_report_or_error(render_result),
    )
    write_redacted_json(
        review_dir / "bounded-review-plan.json",
        bounded_plan.model_dump(mode="json"),
    )
    write_redacted_json(
        review_dir / "bounded-review-coverage.json",
        bounded_coverage.model_dump(mode="json"),
    )
    write_redacted_json(
        review_dir / "bounded-review-coverage-validation.json",
        bounded_validation.model_dump(mode="json"),
    )
    benchmark_comparison = build_candidate_benchmark_comparison(
        repository=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        candidate_sha256=candidate_hash,
        bundle_dir=bundle_dir,
    )
    write_redacted_json(
        planning_dir / "candidate-benchmark-comparison.json",
        benchmark_comparison.model_dump(mode="json"),
    )

    assessment_hash = assessment.canonical_hash()
    presentation_plan_hash = _canonical_hash(presentation_plan.get("presentation_plan") or {})
    manifest_path = bundle_dir / "manifest.json"
    prior_manifest: dict = {}
    if manifest_path.is_file():
        loaded_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(loaded_manifest, dict):
            prior_manifest = loaded_manifest
    initial_origin_hash = candidate_generation_origin_hash(
        source_revision=snapshot.source_revision,
        facts_hash=document_plan.facts_hash,
        assessment_hash=assessment_hash,
        presentation_plan_hash=presentation_plan_hash,
        candidate_hash=candidate_hash,
    )
    repair_budget_origin_hash = (
        prior_manifest.get("repair_budget_origin_hash")
        if candidate_role == "repair"
        else initial_origin_hash
    )
    same_candidate = (
        prior_manifest.get("candidate_hash") == candidate_hash
        and prior_manifest.get("candidate_stage_dependency_key")
        == candidate_component_manifest.stage_key
    )
    completed_stages = [
        "SNAPSHOTTED",
        "PROFILED",
        "FACTS_COLLECTING",
        "FACTS_READY",
        "README_ASSESSED",
        "PLAN_READY",
        "CANDIDATE_GENERATED",
    ]
    if same_candidate:
        for stage in prior_manifest.get("completed_stages", []):
            if isinstance(stage, str) and stage not in completed_stages:
                completed_stages.append(stage)
    lifecycle_status = (
        str(prior_manifest.get("lifecycle_status", "CANDIDATE_GENERATED"))
        if same_candidate
        else "CANDIDATE_GENERATED"
    )
    candidate_llm_accounting = write_candidate_transaction_llm_accounting(bundle_dir)
    write_local_poc_manifest(
        bundle_dir,
        {
            **prior_manifest,
            "schema_version": 1,
            "org_repo": snapshot.org_repo,
            "source_revision": snapshot.source_revision,
            "lifecycle_status": lifecycle_status,
            "facts_hash": document_plan.facts_hash,
            "assessment_hash": assessment_hash,
            "presentation_plan_hash": presentation_plan_hash,
            "agentic_composition_plan_hash": (
                agentic_plan.canonical_hash() if agentic_plan is not None else None
            ),
            "candidate_hash": candidate_hash,
            "candidate_benchmark_comparison_hash": _canonical_hash(
                benchmark_comparison.model_dump(mode="json")
            ),
            "candidate_stage_dependency_key": candidate_component_manifest.stage_key,
            "candidate_stage_dependency_manifest": candidate_component_manifest.model_dump(
                mode="json"
            ),
            "repair_budget_origin_hash": repair_budget_origin_hash,
            **candidate_llm_accounting,
            "complete": bool(prior_manifest.get("complete", False)) if same_candidate else False,
            "completed_stages": completed_stages,
        },
        include_runtime_accounting=include_runtime_accounting,
    )
    refresh_sha256sums(bundle_dir)
    return bundle_dir, assessment_hash, presentation_plan_hash, candidate_hash
