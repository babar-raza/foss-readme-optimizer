"""Validate reusable stage-bounded portfolio product-truth bundles."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.evidence.writer import verify_sha256sums
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.supervisor.portfolio_scheduler.contracts import StageReceiptV1
from readme_agent.supervisor.product_truth import load_prepared_product_truth
from readme_agent.supervisor.stage_limit import (
    ReadmePocStageLimitV1,
    lifecycle_stage_reaches_limit,
)


def completed_bounded_product_truth_status(
    backend: StateBackend,
    org_repo: str,
    bundle_dir: Path,
    requested_stage: ReadmePocStageLimitV1,
    *,
    current_source_revision: str | None,
) -> str | None:
    """Return a reusable bounded status only under current truth contracts."""

    state = backend.load(org_repo)
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if (
        not isinstance(lifecycle, ReadmePocLifecycleStateV2)
        or not lifecycle.source_revision
        or lifecycle.source_revision != current_source_revision
        or not lifecycle_stage_reaches_limit(requested_stage, lifecycle.status)
    ):
        return None
    prepared = load_prepared_product_truth(
        org_repo,
        backend,
        lifecycle.source_revision,
    )
    if prepared is None or not lifecycle_stage_reaches_limit(
        requested_stage,
        prepared.lifecycle_status,
    ):
        return None
    refreshed = backend.load(org_repo)
    refreshed_lifecycle = refreshed.readme_poc_lifecycle if refreshed is not None else None
    if (
        not isinstance(refreshed_lifecycle, ReadmePocLifecycleStateV2)
        or refreshed_lifecycle.source_revision != lifecycle.source_revision
        or refreshed_lifecycle.status != prepared.lifecycle_status
    ):
        return None
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file() or not verify_sha256sums(bundle_dir):
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if (
        manifest.get("org_repo") != org_repo
        or manifest.get("source_revision") != refreshed_lifecycle.source_revision
        or manifest.get("lifecycle_status") != prepared.lifecycle_status
        or manifest.get("facts_hash") != prepared.facts.canonical_hash()
        or requested_stage not in manifest.get("completed_stages", [])
    ):
        return None
    if requested_stage in {"CANDIDATE_GENERATED", "DETERMINISTIC_VALIDATED"}:
        receipt_record = (manifest.get("stage_receipts") or {}).get(requested_stage)
        if not isinstance(receipt_record, dict):
            return None
        receipt_relative = receipt_record.get("receipt_path")
        if not isinstance(receipt_relative, str):
            return None
        receipt_path = bundle_dir / receipt_relative
        try:
            receipt = StageReceiptV1.model_validate_json(receipt_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            return None
        if (
            receipt.target_stage != requested_stage
            or receipt.org_repo != org_repo
            or receipt.source_revision != refreshed_lifecycle.source_revision
            or receipt.campaign_id != manifest.get("campaign_id")
            or receipt.work_id != receipt_record.get("work_id")
            or receipt.output_hash != receipt_record.get("output_hash")
        ):
            return None
    return prepared.lifecycle_status


def completed_bounded_trusted_status(
    backend: StateBackend,
    org_repo: str,
    bundle_dir: Path,
    requested_stage: ReadmePocStageLimitV1,
    *,
    current_source_revision: str | None,
) -> str | None:
    """Return an exact trusted approval/no-op cache without promoting its assurance."""

    if requested_stage not in {"TRUSTED_TRANSFORM_APPROVED", "TRUSTED_NO_OP_PROVEN"}:
        return None
    state = backend.load(org_repo)
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if (
        not isinstance(lifecycle, ReadmePocLifecycleStateV2)
        or lifecycle.content_assurance != "trusted_inherited"
        or lifecycle.source_revision != current_source_revision
        or not lifecycle_stage_reaches_limit(requested_stage, lifecycle.status)
    ):
        return None
    trusted_dir = bundle_dir / "assurance" / "trusted_inherited"
    manifest_path = trusted_dir / "manifest.json"
    facts_path = trusted_dir / "facts" / "readme-inherited-facts.json"
    composition_path = trusted_dir / "planning" / "composition-output.json"
    review_path = trusted_dir / "review" / "review-execution.json"
    required = (manifest_path, facts_path, composition_path, review_path)
    if not all(path.is_file() for path in required) or not verify_sha256sums(trusted_dir):
        return None
    try:
        from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
        from readme_agent.readme.trusted_composition_models import TrustedReadmeCompositionOutputV1
        from readme_agent.specialists.trusted_transform_review_models import (
            TrustedReviewExecutionV1,
        )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        graph = TrustedReadmeFactGraphV1.model_validate_json(facts_path.read_text(encoding="utf-8"))
        composition = TrustedReadmeCompositionOutputV1.model_validate_json(
            composition_path.read_text(encoding="utf-8")
        )
        review = TrustedReviewExecutionV1.model_validate_json(
            review_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None
    if (
        manifest.get("content_assurance") != "trusted_inherited"
        or manifest.get("org_repo") != org_repo
        or manifest.get("source_revision") != current_source_revision
        or manifest.get("lifecycle_status") != lifecycle.status
        or requested_stage not in manifest.get("completed_stages", [])
        or manifest.get("facts_hash") != graph.canonical_hash()
        or manifest.get("candidate_hash") != composition.candidate_sha256
        or lifecycle.facts_hash != graph.canonical_hash()
        or lifecycle.candidate_hash != composition.candidate_sha256
        or review.review.candidate_sha256 != composition.candidate_sha256
        or review.review.verdict != "TRUSTED_TRANSFORM_APPROVED"
    ):
        return None
    if requested_stage == "TRUSTED_NO_OP_PROVEN":
        no_op_path = trusted_dir / "review" / "no-op-proof.json"
        if not no_op_path.is_file():
            return None
        try:
            no_op = json.loads(no_op_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        if no_op.get("passed") is not True:
            return None
    return lifecycle.status
