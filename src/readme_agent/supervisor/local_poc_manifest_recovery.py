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
