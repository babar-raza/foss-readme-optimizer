"""Reconcile an approved compatibility manifest from its accepted stage receipt."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums, sha256_file
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor.local_poc_evidence import write_local_poc_manifest
from readme_agent.supervisor.portfolio_scheduler.contracts import (
    StageReceiptV1,
    canonical_sha256,
)

_STAGE = "CANDIDATE_GENERATED"
_REQUIRED_ARTIFACTS = {
    "assessment/current-readme-assessment.json",
    "candidate/README.md",
    "planning/presentation-plan.json",
}
_COMPLETED_STATUSES = {
    "NO_OP_PROVEN",
    "HUMAN_REVIEW_READY",
    "HUMAN_ACCEPTED",
    "PR_ELIGIBLE",
    "PR_PROOF_COMPLETE",
}
_REVIEW_STAGES = (
    "DETERMINISTIC_VALIDATED",
    "AGENT_REVIEWING",
    "AGENT_APPROVED",
    "NO_OP_PROVEN",
)


def _json_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _accepted_stage_artifacts_match(
    bundle_dir: Path,
    receipt: StageReceiptV1,
) -> bool:
    artifacts = {item.path: item for item in receipt.artifact_inventory}
    if not _REQUIRED_ARTIFACTS.issubset(artifacts):
        return False
    for relative in _REQUIRED_ARTIFACTS:
        path = bundle_dir / relative
        artifact = artifacts[relative]
        if (
            not path.is_file()
            or path.stat().st_size != artifact.size
            or sha256_file(path)[0] != artifact.sha256
        ):
            return False
    return True


def reconcile_approved_manifest_from_receipt(
    state: RunStateV2,
    bundle_dir: Path,
) -> bool:
    """Repair only stale stage-owned hashes after all independent bindings agree."""

    lifecycle = state.readme_poc_lifecycle
    if (
        not isinstance(lifecycle, ReadmePocLifecycleStateV2)
        or lifecycle.status != "AGENT_APPROVED"
        or lifecycle.source_revision is None
        or lifecycle.assessment_hash is None
        or lifecycle.presentation_plan_hash is None
        or lifecycle.candidate_hash is None
    ):
        return False
    manifest_path = bundle_dir / "manifest.json"
    receipt_path = bundle_dir / "receipts" / f"{_STAGE}.json"
    manifest = _json_object(manifest_path)
    try:
        receipt = StageReceiptV1.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return False
    recorded_receipt = (manifest.get("stage_receipts") or {}).get(_STAGE)
    if (
        receipt.target_stage != _STAGE
        or receipt.org_repo != state.org_repo
        or receipt.source_revision != lifecycle.source_revision
        or not isinstance(recorded_receipt, dict)
        or recorded_receipt.get("work_id") != receipt.work_id
        or recorded_receipt.get("output_hash") != receipt.output_hash
        or not _accepted_stage_artifacts_match(bundle_dir, receipt)
    ):
        return False
    assessment = _json_object(bundle_dir / "assessment" / "current-readme-assessment.json")
    presentation_plan = _json_object(bundle_dir / "planning" / "presentation-plan.json")
    try:
        actual_assessment_hash = ReadmeAssessmentV1.model_validate(assessment).canonical_hash()
    except ValueError:
        return False
    actual_candidate_hash = sha256_file(bundle_dir / "candidate" / "README.md")[0]
    actual_plan_hash = canonical_sha256(presentation_plan)
    expected = {
        "assessment_hash": lifecycle.assessment_hash,
        "presentation_plan_hash": lifecycle.presentation_plan_hash,
        "candidate_hash": lifecycle.candidate_hash,
    }
    if expected != {
        "assessment_hash": actual_assessment_hash,
        "presentation_plan_hash": actual_plan_hash,
        "candidate_hash": actual_candidate_hash,
    }:
        return False
    if all(manifest.get(key) == value for key, value in expected.items()):
        return False
    write_local_poc_manifest(bundle_dir, {**manifest, **expected})
    refresh_sha256sums(bundle_dir)
    return True


def reconcile_completed_manifest_from_evidence(
    state: RunStateV2,
    bundle_dir: Path,
) -> bool:
    """Repair a stale candidate-stage manifest from exact completed review evidence."""

    lifecycle = state.readme_poc_lifecycle
    if (
        not isinstance(lifecycle, ReadmePocLifecycleStateV2)
        or lifecycle.status not in _COMPLETED_STATUSES
        or lifecycle.source_revision is None
        or lifecycle.candidate_hash is None
    ):
        return False
    manifest = _json_object(bundle_dir / "manifest.json")
    final_verdict = _json_object(bundle_dir / "review" / "final-verdict.json")
    no_op_proof = _json_object(bundle_dir / "review" / "no-op-proof.json")
    candidate_path = bundle_dir / "candidate" / "README.md"
    if (
        manifest.get("org_repo") != state.org_repo
        or manifest.get("source_revision") != lifecycle.source_revision
        or not candidate_path.is_file()
        or sha256_file(candidate_path)[0] != lifecycle.candidate_hash
        or final_verdict.get("verdict") != "AGENT_APPROVED"
        or final_verdict.get("agent_approved") is not True
        or final_verdict.get("deterministic_validation_passed") is not True
        or no_op_proof.get("verdict") != "NO_OP_PROVEN"
        or no_op_proof.get("candidate_hash") != lifecycle.candidate_hash
        or no_op_proof.get("patch_created") is not False
        or no_op_proof.get("duplicate_bundle_created") is not False
        or no_op_proof.get("agentic_review_reused") is not True
        or no_op_proof.get("llm_accounting_status") != "EXACT"
        or no_op_proof.get("new_provider_call_count") != 0
    ):
        return False
    completed = [str(item) for item in manifest.get("completed_stages", [])]
    for stage in _REVIEW_STAGES:
        if stage not in completed:
            completed.append(stage)
    if lifecycle.status not in completed:
        completed.append(lifecycle.status)
    expected = {
        "lifecycle_status": lifecycle.status,
        "complete": True,
        "completed_stages": completed,
    }
    if all(manifest.get(key) == value for key, value in expected.items()):
        return False
    write_local_poc_manifest(bundle_dir, {**manifest, **expected})
    refresh_sha256sums(bundle_dir)
    return True


__all__ = [
    "reconcile_approved_manifest_from_receipt",
    "reconcile_completed_manifest_from_evidence",
]
