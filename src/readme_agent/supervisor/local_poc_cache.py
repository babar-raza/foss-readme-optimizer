"""Decide whether a completed local README bundle is safe to reuse."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.evidence.writer import sha256_file
from readme_agent.facts.acceptance_contract import (
    classify_product_truth,
    current_fact_acceptance_contract,
)
from readme_agent.facts.local_verification import local_verification_contract_hash
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm import prompt_registry
from readme_agent.llm.verification_prompts import separated_reviewer_standard_hash
from readme_agent.readme.document_templates import document_template_hash
from readme_agent.registry.loader import require_listed
from readme_agent.state.assurance import ContentAssuranceV1
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor.mission_lifecycle_freshness import (
    evaluate_lifecycle_fact_freshness,
)
from readme_agent.supervisor.presentation_component_versions import (
    ComponentDeltaV1,
    classify_component_delta,
)
from readme_agent.supervisor.stage_dependencies import (
    StageDependencyManifestV1,
    current_candidate_stage_dependency_manifest,
)

_COMPLETE_STATUSES = {
    "NO_OP_PROVEN",
    "HUMAN_REVIEW_READY",
    "HUMAN_ACCEPTED",
    "PR_ELIGIBLE",
    "PR_PROOF_COMPLETE",
}


class LocalPocCacheDecisionV1(BaseModel):
    """Inspectably bind one reuse decision to every acceptance dependency."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    content_assurance: ContentAssuranceV1
    status: str | None = None
    reusable: bool
    cache_key: str
    mismatch_reasons: list[str]
    earliest_affected_stage: str | None = None
    stored_dependencies: dict[str, Any]
    current_dependencies: dict[str, Any]
    decision_status: Literal["REUSE_CURRENT", "VALID_UPDATE_AVAILABLE", "INVALIDATED"] = (
        "INVALIDATED"
    )
    fact_validity_preserved: bool = False
    presentation_validity_preserved: bool = False
    update_earliest_stage: str | None = None
    component_delta: ComponentDeltaV1 | None = None


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _load_inventory(bundle_dir: Path) -> tuple[dict[str, str], str | None]:
    path = bundle_dir / "sha256sums.txt"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return {}, None
    expected: dict[str, str] = {}
    for line in lines:
        try:
            digest, relative = line.split("  ", maxsplit=1)
        except ValueError:
            return {}, None
        if (
            len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or not relative
            or relative in expected
        ):
            return {}, None
        expected[relative] = digest
    return expected, sha256_file(path)[0]


def _inventory_valid(bundle_dir: Path, expected: dict[str, str]) -> bool:
    actual = {
        path.relative_to(bundle_dir).as_posix(): path
        for path in bundle_dir.rglob("*")
        if path.is_file() and path.name != "sha256sums.txt"
    }
    return set(expected) == set(actual) and all(
        sha256_file(actual[relative])[0] == digest for relative, digest in expected.items()
    )


def _stored_dependencies(
    state: RunStateV2 | None,
    manifest: dict[str, Any] | None,
    document_plan: dict[str, Any] | None,
    agentic_plan: dict[str, Any] | None,
    inventory_sha256: str | None,
) -> dict[str, Any]:
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    supervisor = state.supervisor_state if state is not None else None
    return {
        "source_revision": getattr(lifecycle, "source_revision", None),
        "content_assurance": getattr(lifecycle, "content_assurance", None),
        "facts_hash": getattr(lifecycle, "facts_hash", None),
        "assessment_hash": getattr(lifecycle, "assessment_hash", None),
        "presentation_plan_hash": getattr(lifecycle, "presentation_plan_hash", None),
        "candidate_hash": getattr(lifecycle, "candidate_hash", None),
        "fact_acceptance_contract_hash": (
            manifest.get("fact_acceptance_contract_hash") if manifest else None
        ),
        "fact_acceptance_component_hashes": (
            manifest.get("fact_acceptance_component_hashes") if manifest else None
        ),
        "local_verification_contract_hash": (
            manifest.get("local_verification_contract_hash") if manifest else None
        ),
        "prompt_registry_content_hash": (
            manifest.get("prompt_registry_content_hash") if manifest else None
        ),
        "prompt_dependency_hashes": (
            manifest.get("prompt_dependency_hashes") if manifest else None
        ),
        "template_hash": document_plan.get("template_sha256") if document_plan else None,
        "composition_prompt_hash": (agentic_plan.get("prompt_sha256") if agentic_plan else None),
        "candidate_stage_dependency_key": (
            manifest.get("candidate_stage_dependency_key") if manifest else None
        ),
        "candidate_stage_dependency_manifest": (
            manifest.get("candidate_stage_dependency_manifest") if manifest else None
        ),
        "reviewer_standard_hash": (manifest.get("reviewer_standard_hash") if manifest else None),
        "control_plane_fingerprint": (
            supervisor.control_plane_fingerprint if supervisor is not None else None
        ),
        "artifact_inventory_sha256": inventory_sha256,
    }


def _current_dependencies(
    *,
    source_revision: str | None,
    control_plane_fingerprint: str,
    inventory_sha256: str | None,
    content_assurance: ContentAssuranceV1,
    org_repo: str,
    ecosystem: str | None = None,
    family: str | None = None,
) -> dict[str, Any]:
    resolved_family = family
    if ecosystem is not None and family is None:
        resolved_family = require_listed(org_repo).family
    fact_contract = current_fact_acceptance_contract(ecosystem, resolved_family)
    component_manifest = current_candidate_stage_dependency_manifest(
        repository=org_repo,
        source_revision=source_revision or "0" * 40,
        ecosystem=ecosystem,
    )
    return {
        "source_revision": source_revision,
        "content_assurance": content_assurance,
        "fact_acceptance_contract_hash": fact_contract.canonical_hash(),
        "fact_acceptance_component_hashes": fact_contract.component_hashes,
        "local_verification_contract_hash": local_verification_contract_hash(ecosystem),
        "prompt_registry_content_hash": prompt_registry.content_hash(),
        "prompt_dependency_hashes": prompt_registry.dependency_hashes(),
        "template_hash": document_template_hash(),
        "composition_prompt_hash": prompt_registry.prompt_hash("plan_readme_composition"),
        "candidate_stage_dependency_key": component_manifest.stage_key,
        "candidate_stage_dependency_manifest": component_manifest.model_dump(mode="json"),
        "reviewer_standard_hash": separated_reviewer_standard_hash(),
        "control_plane_fingerprint": control_plane_fingerprint,
        "artifact_inventory_sha256": inventory_sha256,
    }


def evaluate_completed_local_poc_cache(
    state: RunStateV2 | None,
    bundle_dir: Path,
    *,
    current_source_revision: str | None,
    current_control_plane_fingerprint: str,
    content_assurance: ContentAssuranceV1 = "repository_verified",
    ecosystem: str | None = None,
    family: str | None = None,
) -> LocalPocCacheDecisionV1:
    """Fail closed unless a no-op-proven bundle and every dependency still agree."""

    return _evaluate_local_poc_cache(
        state,
        bundle_dir,
        current_source_revision=current_source_revision,
        current_control_plane_fingerprint=current_control_plane_fingerprint,
        content_assurance=content_assurance,
        ecosystem=ecosystem,
        family=family,
        approved_only=False,
    )


def evaluate_approved_local_poc_cache(
    state: RunStateV2 | None,
    bundle_dir: Path,
    *,
    current_source_revision: str | None,
    current_control_plane_fingerprint: str,
    content_assurance: ContentAssuranceV1 = "repository_verified",
    ecosystem: str | None = None,
    family: str | None = None,
) -> LocalPocCacheDecisionV1:
    """Fail closed unless an approved bundle can prove its first unchanged rerun."""

    return _evaluate_local_poc_cache(
        state,
        bundle_dir,
        current_source_revision=current_source_revision,
        current_control_plane_fingerprint=current_control_plane_fingerprint,
        content_assurance=content_assurance,
        ecosystem=ecosystem,
        family=family,
        approved_only=True,
    )


def _evaluate_local_poc_cache(
    state: RunStateV2 | None,
    bundle_dir: Path,
    *,
    current_source_revision: str | None,
    current_control_plane_fingerprint: str,
    content_assurance: ContentAssuranceV1,
    approved_only: bool,
    ecosystem: str | None,
    family: str | None,
) -> LocalPocCacheDecisionV1:
    """Bind approved or completed reuse to the same complete dependency set."""

    manifest = _load_json(bundle_dir / "manifest.json")
    product_facts_payload = _load_json(bundle_dir / "facts" / "product-facts.json")
    document_plan = _load_json(bundle_dir / "planning" / "readme-document-plan.json")
    agentic_plan = _load_json(bundle_dir / "planning" / "agentic-composition-plan.json")
    final_verdict = _load_json(bundle_dir / "review" / "final-verdict.json")
    no_op_proof = _load_json(bundle_dir / "review" / "no-op-proof.json")
    expected_inventory, inventory_sha256 = _load_inventory(bundle_dir)
    stored = _stored_dependencies(
        state,
        manifest,
        document_plan,
        agentic_plan,
        inventory_sha256,
    )
    current = _current_dependencies(
        source_revision=current_source_revision,
        control_plane_fingerprint=current_control_plane_fingerprint,
        inventory_sha256=inventory_sha256,
        content_assurance=content_assurance,
        org_repo=state.org_repo if state is not None else "unknown/unknown",
        ecosystem=ecosystem,
        family=family,
    )
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    reasons: list[str] = []
    component_delta: ComponentDeltaV1 | None = None

    resolved_family = family
    if ecosystem is not None and resolved_family is None:
        resolved_org_repo = state.org_repo if state is not None else "unknown/unknown"
        resolved_family = require_listed(resolved_org_repo).family
    fact_freshness = evaluate_lifecycle_fact_freshness(
        state,
        bundle_dir,
        current_contract=current_fact_acceptance_contract(ecosystem, resolved_family),
        current_local_verification_hash=current["local_verification_contract_hash"],
        ecosystem=ecosystem,
        family=resolved_family,
    )
    reasons.extend(fact_freshness.mismatch_reasons)

    allowed_statuses = {"AGENT_APPROVED"} if approved_only else _COMPLETE_STATUSES
    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        reasons.append("missing_v2_lifecycle")
    elif lifecycle.status not in allowed_statuses:
        reasons.append("lifecycle_not_approved" if approved_only else "lifecycle_not_complete")
    elif lifecycle.content_assurance != content_assurance:
        reasons.append("content_assurance_changed")
    if manifest is None:
        reasons.append("manifest_missing_or_invalid")
    elif approved_only:
        if manifest.get("lifecycle_status") != "AGENT_APPROVED":
            reasons.append("manifest_approved_status_missing")
        if not isinstance(manifest.get("completed_stages"), list) or (
            "AGENT_APPROVED" not in manifest["completed_stages"]
        ):
            reasons.append("manifest_approved_stage_missing")
    else:
        if manifest.get("complete") is not True:
            reasons.append("manifest_not_complete")
        if not isinstance(manifest.get("completed_stages"), list) or (
            "NO_OP_PROVEN" not in manifest["completed_stages"]
        ):
            reasons.append("manifest_no_op_stage_missing")
    if product_facts_payload is None:
        reasons.append("product_truth_missing_or_invalid")
    else:
        try:
            product_facts = ProductFactsV2.model_validate(product_facts_payload)
        except ValueError:
            reasons.append("product_truth_missing_or_invalid")
        else:
            product_truth_status = classify_product_truth(product_facts)
            if product_truth_status != "FACTS_READY":
                reasons.append(f"product_truth_{product_truth_status.lower()}")
    if document_plan is None:
        reasons.append("document_plan_missing_or_invalid")
    if agentic_plan is None:
        reasons.append("agentic_plan_missing_or_invalid")
    if final_verdict is None:
        reasons.append("final_verdict_missing_or_invalid")
    elif (
        final_verdict.get("verdict") != "AGENT_APPROVED"
        or final_verdict.get("agent_approved") is not True
        or final_verdict.get("deterministic_validation_passed") is not True
    ):
        reasons.append("final_verdict_not_approved")
    if not approved_only:
        if no_op_proof is None:
            reasons.append("no_op_proof_missing_or_invalid")
        elif (
            no_op_proof.get("verdict") != "NO_OP_PROVEN"
            or no_op_proof.get("candidate_hash")
            != (getattr(lifecycle, "candidate_hash", None) if lifecycle is not None else None)
            or no_op_proof.get("patch_created") is not False
            or no_op_proof.get("duplicate_bundle_created") is not False
            or no_op_proof.get("agentic_review_reused") is not True
            or no_op_proof.get("llm_accounting_status") != "EXACT"
            or no_op_proof.get("new_provider_call_count") != 0
        ):
            reasons.append("no_op_proof_invalid")
    if inventory_sha256 is None or not _inventory_valid(bundle_dir, expected_inventory):
        reasons.append("artifact_inventory_invalid")

    if isinstance(lifecycle, ReadmePocLifecycleStateV2) and manifest is not None:
        manifest_bindings = {
            "org_repo": state.org_repo if state is not None else None,
            "source_revision": lifecycle.source_revision,
            "content_assurance": lifecycle.content_assurance,
            "lifecycle_status": lifecycle.status,
            "facts_hash": lifecycle.facts_hash,
            "assessment_hash": lifecycle.assessment_hash,
            "presentation_plan_hash": lifecycle.presentation_plan_hash,
            "candidate_hash": lifecycle.candidate_hash,
            "prompt_hash": lifecycle.prompt_hash,
            "fact_acceptance_contract_hash": lifecycle.fact_acceptance_contract_hash,
            "fact_acceptance_component_hashes": lifecycle.fact_acceptance_component_hashes,
            "reviewer_standard_hash": lifecycle.reviewer_standard_hash,
            "repair_budget_origin_hash": lifecycle.repair_budget_origin_hash,
        }
        for field, expected in manifest_bindings.items():
            actual = (
                manifest.get(field, "repository_verified")
                if field == "content_assurance"
                else manifest.get(field)
            )
            if actual != expected:
                reasons.append(f"manifest_{field}_mismatch")

    for field in (
        "source_revision",
        "content_assurance",
        "fact_acceptance_contract_hash",
        "fact_acceptance_component_hashes",
        "local_verification_contract_hash",
        "reviewer_standard_hash",
    ):
        if stored.get(field) != current.get(field):
            reasons.append(f"{field}_changed")
    stored_component_payload = stored.get("candidate_stage_dependency_manifest")
    current_component_payload = current.get("candidate_stage_dependency_manifest")
    try:
        stored_component_manifest = StageDependencyManifestV1.model_validate(
            stored_component_payload
        )
        current_component_manifest = StageDependencyManifestV1.model_validate(
            current_component_payload
        )
    except ValueError:
        reasons.append("candidate_stage_dependency_manifest_missing_or_invalid")
    else:
        component_delta = classify_component_delta(
            stored_component_manifest,
            current_component_manifest,
        )
        if component_delta.outcome == "INVALIDATED":
            reasons.extend(
                f"presentation_component_{scope}_changed"
                for scope in component_delta.changed_scopes
            )
    stored_prompt_dependencies = stored.get("prompt_dependency_hashes")
    current_prompt_dependencies = current.get("prompt_dependency_hashes")
    prompt_components_account_for_delta = bool(
        component_delta is not None
        and component_delta.outcome in {"VALID_UPDATE_AVAILABLE", "INVALIDATED"}
        and component_delta.changed_component_ids
        and any(
            component_id.startswith("prompt:")
            for component_id in component_delta.changed_component_ids
        )
    )
    if not isinstance(stored_prompt_dependencies, dict):
        reasons.append("prompt_dependency_hashes_missing")
    elif (
        stored_prompt_dependencies != current_prompt_dependencies
        and not prompt_components_account_for_delta
    ):
        current_scopes = (
            current_prompt_dependencies if isinstance(current_prompt_dependencies, dict) else {}
        )
        for scope in sorted(set(stored_prompt_dependencies) | set(current_scopes)):
            if stored_prompt_dependencies.get(scope) != current_scopes.get(scope):
                reasons.append(f"prompt_scope_{scope}_changed")
    elif (
        stored.get("prompt_registry_content_hash") != current.get("prompt_registry_content_hash")
        and not prompt_components_account_for_delta
    ):
        # The aggregate hashes remain a fail-closed consistency guard. They are
        # suppressed only when the independently versioned prompt components
        # identify the same semantic delta.
        reasons.append("prompt_registry_content_hash_changed")

    if stored.get("control_plane_fingerprint") != current.get("control_plane_fingerprint"):
        prompt_change_is_semantically_accounted = bool(
            component_delta is not None
            and component_delta.outcome == "VALID_UPDATE_AVAILABLE"
            and stored.get("prompt_registry_content_hash")
            != current.get("prompt_registry_content_hash")
            and any(
                component_id.startswith("prompt:")
                for component_id in component_delta.changed_component_ids
            )
        )
        critical_change_is_already_accounted = bool(
            component_delta is not None and component_delta.outcome == "INVALIDATED"
        )
        if not prompt_change_is_semantically_accounted and not critical_change_is_already_accounted:
            reasons.append("control_plane_fingerprint_changed")

    reasons = sorted(set(reasons))
    earliest_affected_stage = _earliest_affected_stage(reasons)
    if component_delta is not None and component_delta.outcome == "INVALIDATED":
        component_stage = component_delta.earliest_affected_stage
        if component_stage is not None and (
            earliest_affected_stage is None
            or _STAGE_ORDER[component_stage] < _STAGE_ORDER[earliest_affected_stage]
        ):
            earliest_affected_stage = component_stage
    key_material = {
        "org_repo": state.org_repo if state is not None else None,
        "stored": stored,
        "current": current,
    }
    valid_update_available = bool(
        not reasons
        and component_delta is not None
        and component_delta.outcome == "VALID_UPDATE_AVAILABLE"
    )
    reusable = not reasons and not valid_update_available
    decision_status: Literal["REUSE_CURRENT", "VALID_UPDATE_AVAILABLE", "INVALIDATED"] = (
        "VALID_UPDATE_AVAILABLE"
        if valid_update_available
        else ("REUSE_CURRENT" if reusable else "INVALIDATED")
    )
    return LocalPocCacheDecisionV1(
        content_assurance=content_assurance,
        status=(
            lifecycle.status
            if decision_status != "INVALIDATED" and isinstance(lifecycle, ReadmePocLifecycleStateV2)
            else None
        ),
        reusable=reusable,
        cache_key=_canonical_sha256(key_material),
        mismatch_reasons=reasons,
        earliest_affected_stage=earliest_affected_stage,
        stored_dependencies=stored,
        current_dependencies=current,
        decision_status=decision_status,
        fact_validity_preserved=(
            component_delta.fact_validity_preserved if component_delta is not None else reusable
        ),
        presentation_validity_preserved=(
            component_delta.presentation_validity_preserved
            if component_delta is not None
            else reusable
        ),
        update_earliest_stage=(
            component_delta.earliest_affected_stage
            if valid_update_available and component_delta is not None
            else None
        ),
        component_delta=component_delta,
    )


_STAGE_ORDER = {
    "SNAPSHOTTED": 0,
    "FACTS_COLLECTING": 1,
    "README_ASSESSED": 2,
    "PLAN_READY": 3,
    "CANDIDATE_GENERATED": 4,
    "AGENT_REVIEWING": 5,
}


def _earliest_affected_stage(reasons: list[str]) -> str | None:
    """Map invalid inputs to the first stage that must be recomputed."""

    affected: list[str] = []
    for reason in reasons:
        if reason in {"missing_v2_lifecycle", "source_revision_changed"}:
            affected.append("SNAPSHOTTED")
        elif reason == "content_assurance_changed":
            affected.append("FACTS_COLLECTING")
        elif reason.startswith("prompt_scope_"):
            scope = reason.removeprefix("prompt_scope_").removesuffix("_changed")
            if scope in {"DETERMINISTIC_VALIDATED", "REPAIRING"}:
                affected.append("CANDIDATE_GENERATED")
            else:
                affected.append(scope if scope in _STAGE_ORDER else "FACTS_COLLECTING")
        elif (
            reason.startswith("fact_")
            or reason.startswith("agent_draft_")
            or reason.startswith("product_truth_")
            or reason.startswith("manifest_facts_")
            or reason.startswith("manifest_local_verification_")
            or reason == "local_verification_contract_hash_changed"
            or reason == "draft_product_truth_prompt_hash_changed"
            or reason == "prompt_registry_content_hash_changed"
            or reason == "prompt_dependency_hashes_missing"
            or reason == "control_plane_fingerprint_changed"
        ):
            affected.append("FACTS_COLLECTING")
        elif reason.startswith("manifest_assessment_"):
            affected.append("README_ASSESSED")
        elif reason.startswith("manifest_presentation_plan_") or reason in {
            "template_hash_changed",
            "composition_prompt_hash_changed",
            "candidate_stage_dependency_key_changed",
            "candidate_stage_dependency_manifest_missing_or_invalid",
        }:
            affected.append("PLAN_READY")
        elif reason.startswith("manifest_candidate_") or reason in {
            "artifact_inventory_invalid",
            "manifest_no_op_stage_missing",
            "manifest_repair_budget_origin_hash_mismatch",
        }:
            affected.append("CANDIDATE_GENERATED")
        elif reason in {
            "reviewer_standard_hash_changed",
            "final_verdict_missing_or_invalid",
            "final_verdict_not_approved",
            "no_op_proof_missing_or_invalid",
            "no_op_proof_invalid",
        }:
            affected.append("AGENT_REVIEWING")
        elif reason.startswith("presentation_component_"):
            # The typed component manifest owns this boundary. Its independently
            # versioned earliest stage is applied after the reason scan.
            continue
        else:
            affected.append("SNAPSHOTTED")
    return min(affected, key=_STAGE_ORDER.__getitem__) if affected else None
