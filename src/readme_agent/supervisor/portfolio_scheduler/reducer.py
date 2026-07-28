"""Sole promoter for sealed stage artifacts, receipts, and lifecycle state."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.readme_poc_lifecycle import (
    record_readme_candidate_artifacts,
    transition_readme_poc_status,
)
from readme_agent.supervisor.local_poc_evidence import write_local_poc_manifest
from readme_agent.supervisor.portfolio_scheduler.contracts import (
    PortfolioStageWorkItemV1,
    StageReceiptV1,
)
from readme_agent.supervisor.portfolio_scheduler.lane import (
    atomic_copy_file,
    validate_sealed_stage_attempt,
)


def _fence_matches(work: PortfolioStageWorkItemV1, lifecycle: object) -> bool:
    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        return False
    fence = work.fence
    return (
        lifecycle.source_revision == fence.source_revision
        and lifecycle.status == fence.lifecycle_status
        and lifecycle.facts_hash == fence.facts_hash
        and lifecycle.fact_acceptance_contract_hash == fence.fact_acceptance_contract_hash
        and lifecycle.prompt_hash == fence.prompt_hash
        and lifecycle.candidate_hash == fence.candidate_hash
    )


def _stable_inputs_match(work: PortfolioStageWorkItemV1, lifecycle: object) -> bool:
    """Allow receipt recovery after status advancement, never after input drift."""

    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        return False
    fence = work.fence
    return (
        lifecycle.source_revision == fence.source_revision
        and lifecycle.facts_hash == fence.facts_hash
        and lifecycle.fact_acceptance_contract_hash == fence.fact_acceptance_contract_hash
        and lifecycle.prompt_hash == fence.prompt_hash
    )


def _receipt_path(work: PortfolioStageWorkItemV1) -> Path:
    org, repo = work.fence.org_repo.split("/", maxsplit=1)
    from readme_agent import paths

    return (
        paths.readme_poc_campaign_repository_dir(
            work.campaign_id,
            org,
            repo,
            work.fence.source_revision,
        )
        / "receipts"
        / f"{work.target_stage}.json"
    )


def _load_matching_receipt(
    work: PortfolioStageWorkItemV1,
    output_hash: str,
) -> StageReceiptV1 | None:
    path = _receipt_path(work)
    if not path.is_file():
        return None
    receipt = StageReceiptV1.model_validate_json(path.read_text(encoding="utf-8"))
    if receipt.work_id != work.work_id or receipt.output_hash != output_hash:
        raise ValueError("a different result already owns this stage receipt")
    return receipt


def _promote_artifacts(
    attempt_root: Path,
    compatibility_bundle: Path,
    receipt: StageReceiptV1,
) -> None:
    for artifact in receipt.artifact_inventory:
        if artifact.path in {"manifest.json", "sha256sums.txt"}:
            continue
        atomic_copy_file(
            attempt_root / "artifacts" / artifact.path,
            compatibility_bundle / artifact.path,
        )
    receipt_view = compatibility_bundle / "receipts" / f"{receipt.target_stage}.json"
    write_redacted_json(receipt_view, receipt)
    manifest_path = compatibility_bundle / "manifest.json"
    current_manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    )
    attempt_manifest_path = attempt_root / "artifacts" / "manifest.json"
    attempt_manifest = (
        json.loads(attempt_manifest_path.read_text(encoding="utf-8"))
        if attempt_manifest_path.is_file()
        else {}
    )
    completed_stages = current_manifest.get("completed_stages") or []
    manifest = (
        current_manifest
        if receipt.target_stage in completed_stages
        else {**current_manifest, **attempt_manifest}
    )
    stage_receipts = dict(manifest.get("stage_receipts") or {})
    stage_receipts[receipt.target_stage] = {
        "campaign_id": receipt.campaign_id,
        "work_id": receipt.work_id,
        "output_hash": receipt.output_hash,
        "receipt_path": receipt_view.relative_to(compatibility_bundle).as_posix(),
    }
    write_local_poc_manifest(
        compatibility_bundle,
        {
            **manifest,
            "campaign_id": receipt.campaign_id,
            "acceptance_authority": "sealed_stage_receipts",
            "stage_receipts": stage_receipts,
        },
    )
    refresh_sha256sums(compatibility_bundle)


def _accept_receipt(
    work: PortfolioStageWorkItemV1,
    attempt_root: Path,
) -> StageReceiptV1:
    result, seal = validate_sealed_stage_attempt(work, attempt_root)
    existing = _load_matching_receipt(work, result.output_hash)
    if existing is not None:
        return existing
    receipt = StageReceiptV1(
        campaign_id=work.campaign_id,
        work_id=work.work_id,
        target_stage=work.target_stage,
        org_repo=work.fence.org_repo,
        source_revision=work.fence.source_revision,
        fence_token=work.fence.fence_token,
        output_hash=result.output_hash,
        result_sha256=seal.result_sha256,
        artifact_inventory=result.artifacts,
    )
    write_redacted_json(_receipt_path(work), receipt)
    return receipt


def promote_candidate_stage(
    work: PortfolioStageWorkItemV1,
    attempt_root: Path,
    compatibility_bundle: Path,
    backend: StateBackend,
    *,
    assessment_hash: str,
    presentation_plan_hash: str,
    candidate_hash: str,
    reviewer_standard_hash: str,
) -> StageReceiptV1:
    """Promote candidate bytes and lifecycle once after a fresh fence check."""

    result, _seal = validate_sealed_stage_attempt(work, attempt_root)
    existing = _load_matching_receipt(work, result.output_hash)
    state = backend.load(work.fence.org_repo)
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if existing is None and not _fence_matches(work, lifecycle):
        raise ValueError("stage fence is stale; refusing candidate promotion")
    if existing is not None and not _stable_inputs_match(work, lifecycle):
        raise ValueError("candidate receipt inputs no longer match durable lifecycle")
    if (
        work.dependency_hashes.get("assessment") != assessment_hash
        or work.dependency_hashes.get("presentation_plan") != presentation_plan_hash
        or work.dependency_hashes.get("candidate") != candidate_hash
        or work.dependency_hashes.get("reviewer_standard") != reviewer_standard_hash
    ):
        raise ValueError("candidate promotion arguments disagree with sealed work dependencies")
    receipt = existing or _accept_receipt(work, attempt_root)
    _promote_artifacts(attempt_root, compatibility_bundle, receipt)
    record_readme_candidate_artifacts(
        backend,
        work.fence.org_repo,
        source_revision=work.fence.source_revision,
        assessment_hash=assessment_hash,
        presentation_plan_hash=presentation_plan_hash,
        candidate_hash=candidate_hash,
        reviewer_standard_hash=reviewer_standard_hash,
        evidence_refs=[
            str(_receipt_path(work)),
            str(compatibility_bundle / "receipts" / "CANDIDATE_GENERATED.json"),
        ],
    )
    return receipt


def promote_deterministic_validation_stage(
    work: PortfolioStageWorkItemV1,
    attempt_root: Path,
    compatibility_bundle: Path,
    backend: StateBackend,
) -> StageReceiptV1:
    """Promote a deterministic pass and resume safely after any cut point."""

    result, _seal = validate_sealed_stage_attempt(work, attempt_root)
    existing = _load_matching_receipt(work, result.output_hash)
    state = backend.load(work.fence.org_repo)
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if existing is None and not _fence_matches(work, lifecycle):
        raise ValueError("stage fence is stale; refusing deterministic-validation promotion")
    if existing is not None and not _stable_inputs_match(work, lifecycle):
        raise ValueError("deterministic receipt inputs no longer match durable lifecycle")
    if work.dependency_hashes.get("candidate") != work.fence.candidate_hash:
        raise ValueError("deterministic work candidate dependency disagrees with its fence")
    receipt = existing or _accept_receipt(work, attempt_root)
    _promote_artifacts(attempt_root, compatibility_bundle, receipt)
    refreshed = backend.load(work.fence.org_repo)
    lifecycle = refreshed.readme_poc_lifecycle if refreshed is not None else None
    if (
        isinstance(lifecycle, ReadmePocLifecycleStateV2)
        and lifecycle.status == "CANDIDATE_GENERATED"
    ):
        transition_readme_poc_status(
            backend,
            work.fence.org_repo,
            "DETERMINISTIC_VALIDATED",
            observed_by="portfolio-stage-reducer",
            reason="sealed deterministic README validation receipt promoted",
            evidence_refs=[
                str(_receipt_path(work)),
                str(compatibility_bundle / "receipts" / "DETERMINISTIC_VALIDATED.json"),
            ],
        )
    elif not (
        isinstance(lifecycle, ReadmePocLifecycleStateV2)
        and lifecycle.status
        in {
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
            "AGENT_APPROVED",
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        }
    ):
        raise ValueError("deterministic-validation receipt cannot advance current lifecycle")
    return receipt
