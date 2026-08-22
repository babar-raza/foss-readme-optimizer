"""Derive one `ProofStageReceiptV1` from existing, already-authoritative repository state.

Pure observation: reads `ReadmePocLifecycleStateV2` (durable state) and, for the
FACTUAL_REVIEWED/VISITOR_REVIEWED split lifecycle state alone cannot express, checks for the
existence of the two already-separated review artifacts
(`review/factual-plan-review.json`/`review/blind-quality-review.json` under the compatibility
bundle -- see `supervisor/local_poc_review_evidence.py`). Never writes lifecycle state, never
promotes anything -- `supervisor/portfolio_scheduler/reducer.py` remains the sole promotion
authority for the durable lifecycle itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from readme_agent import paths
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.supervisor.portfolio_proof_engine.contracts import (
    ProofStageReceiptV1,
    ProofStageV1,
    RubricAcceptanceOutcome,
)
from readme_agent.supervisor.portfolio_proof_engine.section_authoring_adapter import (
    resolve_section_authoring_progress,
)

_BLOCKED_STATUSES = {"BLOCKED_FACT_CONFLICT", "BLOCKED_MISSING_EVIDENCE"}
_REVIEW_READY_OR_LATER = {
    "AGENT_APPROVED",
    "NO_OP_PROVEN",
    "HUMAN_REVIEW_READY",
    "HUMAN_ACCEPTED",
    "PR_ELIGIBLE",
    "PR_PROOF_COMPLETE",
}


def _compatibility_bundle_dir(org_repo: str, source_revision: str | None) -> Path | None:
    if not source_revision:
        return None
    org, repo = org_repo.split("/", maxsplit=1)
    return paths.readme_poc_repository_dir(org, repo, source_revision)


def _bounded_reason(lifecycle: ReadmePocLifecycleStateV2) -> str:
    details = lifecycle.details or {}
    reason = details.get("reason") or details.get("blocked_reason")
    if not reason:
        reason = f"lifecycle status {lifecycle.status}"
    return str(reason)[:500]


def _receipt(
    common: dict[str, Any],
    identity: dict[str, Any],
    *,
    stage: ProofStageV1,
    status: Literal["OK", "FAILED"],
    failure_reason: str | None = None,
) -> ProofStageReceiptV1:
    """Single validated-construction seam so every branch below stays a one-liner and mypy
    checks the merged payload once, rather than fighting per-branch `**dict` unpacking."""

    return ProofStageReceiptV1.model_validate(
        {
            **common,
            **identity,
            "stage": stage,
            "status": status,
            "failure_reason": failure_reason,
        }
    )


def classify_repository_stage(
    org_repo: str,
    backend: StateBackend,
    *,
    predecessor: ProofStageReceiptV1 | None = None,
    ecosystem: str | None = None,
    elapsed_seconds: float = 0.0,
    provider_call_count: int | None = 0,
    rubric_result: RubricAcceptanceOutcome | None = None,
) -> ProofStageReceiptV1:
    """Classify one repository's current stage from its durable lifecycle state alone (plus a
    cheap existence check of the two already-separated review artifacts). `rubric_result`, when
    supplied by the caller after running `rubric.py`, distinguishes RUBRIC_SCORED (scored, not
    accepted) from ACCEPTED (scored, accepted, zero disqualifiers)."""

    common: dict[str, Any] = {
        "org_repo": org_repo,
        "ecosystem": ecosystem,
        "predecessor_receipt_hash": predecessor.canonical_hash() if predecessor else None,
        "elapsed_seconds": elapsed_seconds,
        "provider_call_count": provider_call_count,
    }
    state = backend.load(org_repo)
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        return _receipt(
            common,
            {},
            stage="SOURCE_BOUND",
            status="FAILED",
            failure_reason="no V2 local-POC lifecycle observed yet for this repository",
        )

    identity: dict[str, Any] = {
        "source_revision": lifecycle.source_revision,
        "contract_hash": lifecycle.fact_acceptance_contract_hash,
        "facts_hash": lifecycle.facts_hash,
        "prompt_hash": lifecycle.prompt_hash,
        "candidate_hash": lifecycle.candidate_hash,
        "version_hash": lifecycle.reviewer_standard_hash,
    }
    status = lifecycle.status

    if status == "SYSTEM_FAILURE":
        return _receipt(
            common,
            identity,
            stage="SYSTEM_FAILURE",
            status="FAILED",
            failure_reason=_bounded_reason(lifecycle),
        )
    if status in _BLOCKED_STATUSES:
        return _receipt(
            common,
            identity,
            stage="BLOCKED_INPUT",
            status="FAILED",
            failure_reason=_bounded_reason(lifecycle),
        )
    if status == "DETERMINISTIC_VALIDATION_FAILED":
        return _receipt(
            common,
            identity,
            stage="CANDIDATE_ASSEMBLED",
            status="FAILED",
            failure_reason=_bounded_reason(lifecycle),
        )
    if status == "AGENT_REVIEW_REJECTED":
        return _receipt(
            common,
            identity,
            stage="DETERMINISTIC_VALIDATED",
            status="FAILED",
            failure_reason=_bounded_reason(lifecycle),
        )
    if status in {"DISCOVERED", "INTAKE_PREFLIGHTING", "INTAKE_READY"}:
        return _receipt(common, identity, stage="SOURCE_BOUND", status="OK")
    if status in {"SNAPSHOTTED", "PROFILED", "FACTS_COLLECTING"}:
        return _receipt(common, identity, stage="SOURCE_BOUND", status="OK")
    if status in {"FACTS_READY", "README_ASSESSED", "PLAN_READY"}:
        section_progress = resolve_section_authoring_progress(
            org_repo,
            lifecycle.source_revision,
            lifecycle.facts_hash,
        )
        stage: ProofStageV1
        if section_progress is not None and section_progress.sections_authored:
            stage = "SECTIONS_AUTHORED"
        elif section_progress is not None and section_progress.packets_ready:
            stage = "SECTION_PACKETS_READY"
        else:
            stage = "FACTS_READY"
        return _receipt(common, identity, stage=stage, status="OK")
    if status in {"CANDIDATE_GENERATED", "REPAIRING"}:
        return _receipt(common, identity, stage="CANDIDATE_ASSEMBLED", status="OK")
    if status in {"DETERMINISTIC_VALIDATED", "AGENT_REVIEWING"}:
        return _receipt(common, identity, stage="DETERMINISTIC_VALIDATED", status="OK")
    if status in _REVIEW_READY_OR_LATER:
        bundle_dir = _compatibility_bundle_dir(org_repo, lifecycle.source_revision)
        factual_reviewed = bool(
            bundle_dir and (bundle_dir / "review" / "factual-plan-review.json").is_file()
        )
        visitor_reviewed = bool(
            bundle_dir and (bundle_dir / "review" / "blind-quality-review.json").is_file()
        )
        if rubric_result is not None:
            if rubric_result.accepted:
                return _receipt(common, identity, stage="ACCEPTED", status="OK")
            return _receipt(
                common,
                identity,
                stage="RUBRIC_SCORED",
                status="FAILED",
                failure_reason=rubric_result.bounded_summary(),
            )
        if visitor_reviewed:
            return _receipt(common, identity, stage="VISITOR_REVIEWED", status="OK")
        if factual_reviewed:
            return _receipt(common, identity, stage="FACTUAL_REVIEWED", status="OK")
        return _receipt(common, identity, stage="DETERMINISTIC_VALIDATED", status="OK")
    # Unknown/future lifecycle status: fail closed rather than guess a stage.
    return _receipt(
        common,
        identity,
        stage="SYSTEM_FAILURE",
        status="FAILED",
        failure_reason=f"unclassified lifecycle status {status!r}"[:500],
    )
