"""Decide whether a completed local README bundle is safe to reuse."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from readme_agent.evidence.writer import sha256_file
from readme_agent.facts.acceptance_contract import current_fact_acceptance_contract
from readme_agent.facts.local_verification import local_verification_contract_hash
from readme_agent.llm import prompt_registry
from readme_agent.llm.verification_prompts import separated_reviewer_standard_hash
from readme_agent.readme.document_templates import document_template_hash
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2

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
    status: str | None = None
    reusable: bool
    cache_key: str
    mismatch_reasons: list[str]
    stored_dependencies: dict[str, Any]
    current_dependencies: dict[str, Any]


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
        "template_hash": document_plan.get("template_sha256") if document_plan else None,
        "composition_prompt_hash": (agentic_plan.get("prompt_sha256") if agentic_plan else None),
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
) -> dict[str, Any]:
    fact_contract = current_fact_acceptance_contract()
    return {
        "source_revision": source_revision,
        "fact_acceptance_contract_hash": fact_contract.canonical_hash(),
        "fact_acceptance_component_hashes": fact_contract.component_hashes,
        "local_verification_contract_hash": local_verification_contract_hash(),
        "prompt_registry_content_hash": prompt_registry.content_hash(),
        "template_hash": document_template_hash(),
        "composition_prompt_hash": prompt_registry.prompt_hash("plan_readme_composition"),
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
) -> LocalPocCacheDecisionV1:
    """Fail closed unless every stored and current dependency still agrees."""

    manifest = _load_json(bundle_dir / "manifest.json")
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
    )
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    reasons: list[str] = []

    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        reasons.append("missing_v2_lifecycle")
    elif lifecycle.status not in _COMPLETE_STATUSES:
        reasons.append("lifecycle_not_complete")
    if manifest is None:
        reasons.append("manifest_missing_or_invalid")
    elif manifest.get("complete") is not True:
        reasons.append("manifest_not_complete")
    elif not isinstance(manifest.get("completed_stages"), list) or (
        "NO_OP_PROVEN" not in manifest["completed_stages"]
    ):
        reasons.append("manifest_no_op_stage_missing")
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
            "lifecycle_status": lifecycle.status,
            "facts_hash": lifecycle.facts_hash,
            "assessment_hash": lifecycle.assessment_hash,
            "presentation_plan_hash": lifecycle.presentation_plan_hash,
            "candidate_hash": lifecycle.candidate_hash,
            "prompt_hash": lifecycle.prompt_hash,
            "fact_acceptance_contract_hash": lifecycle.fact_acceptance_contract_hash,
            "fact_acceptance_component_hashes": lifecycle.fact_acceptance_component_hashes,
            "reviewer_standard_hash": lifecycle.reviewer_standard_hash,
        }
        for field, expected in manifest_bindings.items():
            if manifest.get(field) != expected:
                reasons.append(f"manifest_{field}_mismatch")

    for field in (
        "source_revision",
        "fact_acceptance_contract_hash",
        "fact_acceptance_component_hashes",
        "local_verification_contract_hash",
        "prompt_registry_content_hash",
        "template_hash",
        "composition_prompt_hash",
        "reviewer_standard_hash",
        "control_plane_fingerprint",
    ):
        if stored.get(field) != current.get(field):
            reasons.append(f"{field}_changed")

    reasons = sorted(set(reasons))
    key_material = {
        "org_repo": state.org_repo if state is not None else None,
        "stored": stored,
        "current": current,
    }
    reusable = not reasons
    return LocalPocCacheDecisionV1(
        status=(
            lifecycle.status
            if reusable and isinstance(lifecycle, ReadmePocLifecycleStateV2)
            else None
        ),
        reusable=reusable,
        cache_key=_canonical_sha256(key_material),
        mismatch_reasons=reasons,
        stored_dependencies=stored,
        current_dependencies=current,
    )
