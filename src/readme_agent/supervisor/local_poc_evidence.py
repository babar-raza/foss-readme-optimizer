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
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.agentic_composition import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.claim_map import ReadmeClaimMapV1
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.state.readme_poc_lifecycle import candidate_generation_origin_hash
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
            "fact_acceptance_contract_hash": fact_acceptance_contract_hash,
            "fact_acceptance_component_hashes": fact_acceptance_component_hashes,
            "complete": False,
            "completed_stages": ["SNAPSHOTTED", "PROFILED", lifecycle_status],
        },
    )
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
    patch_text = str(presentation_plan.get("git_patch_proof", {}).get("patch") or "")

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
            "candidate_stage_dependency_key": candidate_component_manifest.stage_key,
            "candidate_stage_dependency_manifest": candidate_component_manifest.model_dump(
                mode="json"
            ),
            "repair_budget_origin_hash": repair_budget_origin_hash,
            "complete": bool(prior_manifest.get("complete", False)) if same_candidate else False,
            "completed_stages": completed_stages,
        },
        include_runtime_accounting=include_runtime_accounting,
    )
    refresh_sha256sums(bundle_dir)
    return bundle_dir, assessment_hash, presentation_plan_hash, candidate_hash
