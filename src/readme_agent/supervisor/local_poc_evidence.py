"""Materialize revision-addressed local-POC snapshot evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from readme_agent import paths
from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm import prompt_registry
from readme_agent.llm.bundle_accounting import local_bundle_llm_accounting_fields
from readme_agent.readme.agentic_composition import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.claim_map import ReadmeClaimMapV1
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
from readme_agent.repository_snapshot import RepositorySnapshotV1


def _existing_manifest(bundle_dir: Path, source_revision: str) -> dict:
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file():
        return {}
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or loaded.get("source_revision") != source_revision:
        return {}
    return loaded


def write_local_poc_manifest(bundle_dir: Path, manifest: dict) -> None:
    """Write one bundle manifest with cumulative, fail-closed LLM accounting."""

    path = bundle_dir / "manifest.json"
    prior: dict = {}
    if path.is_file():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            prior = loaded
    write_redacted_json(
        path,
        {
            **manifest,
            "prompt_registry_content_hash": prompt_registry.content_hash(),
            "prompt_hashes_by_id": prompt_registry.prompt_hashes(),
            "prompt_dependency_hashes": prompt_registry.dependency_hashes(),
            **local_bundle_llm_accounting_fields(bundle_dir, prior),
        },
    )


def write_local_poc_snapshot(snapshot: RepositorySnapshotV1) -> Path:
    """Write the immutable source portion of one local-POC bundle idempotently.

    This deliberately records only the boundary actually reached.  Facts,
    plans, candidates, reviews, and the final manifest are owned by their
    later stages; writing placeholders for them would make an incomplete run
    look presentation-ready.
    """
    org, repo = snapshot.org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, snapshot.source_revision)
    prior_manifest = _existing_manifest(bundle_dir, snapshot.source_revision)
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
    if not prior_manifest:
        write_local_poc_manifest(
            bundle_dir,
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
    if _existing_manifest(bundle_dir, snapshot.source_revision).get("candidate_hash"):
        refresh_sha256sums(bundle_dir)
        return
    write_local_poc_manifest(
        bundle_dir,
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
    local_verification_contract_hash: str,
    fact_acceptance_contract_hash: str,
    fact_acceptance_component_hashes: dict[str, str],
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
    facts_hash = facts.canonical_hash()
    prior_manifest = _existing_manifest(bundle_dir, snapshot.source_revision)
    if (
        prior_manifest.get("candidate_hash")
        and prior_manifest.get("facts_hash") == facts_hash
        and prior_manifest.get("prompt_hash") == prompt_hash
        and prior_manifest.get("local_verification_contract_hash")
        == local_verification_contract_hash
        and prior_manifest.get("fact_acceptance_contract_hash") == fact_acceptance_contract_hash
        and prior_manifest.get("fact_acceptance_component_hashes")
        == fact_acceptance_component_hashes
    ):
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


def bind_local_poc_fact_acceptance(
    bundle_dir: Path,
    *,
    source_revision: str,
    contract_hash: str,
    component_hashes: dict[str, str],
) -> None:
    """Attach the current contract to a still-valid later-stage manifest."""

    manifest = _existing_manifest(bundle_dir, source_revision)
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

    manifest = _existing_manifest(bundle_dir, source_revision)
    if not manifest:
        raise RuntimeError(
            f"cannot reclassify fact acceptance without a matching manifest at {bundle_dir}"
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
    same_candidate = prior_manifest.get("candidate_hash") == candidate_hash
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
            "complete": bool(prior_manifest.get("complete", False)) if same_candidate else False,
            "completed_stages": completed_stages,
        },
    )
    refresh_sha256sums(bundle_dir)
    return bundle_dir, assessment_hash, presentation_plan_hash, candidate_hash
