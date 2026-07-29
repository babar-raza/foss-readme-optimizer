"""Persist independently verified local-POC review and no-op evidence."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
)
from readme_agent.supervisor.local_poc_evidence import write_local_poc_manifest


def _load_manifest(bundle_dir: Path) -> dict:
    path = bundle_dir / "manifest.json"
    if not path.is_file():
        raise ValueError(f"local README-POC manifest is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"local README-POC manifest is not an object: {path}")
    return value


def _completed_stages(manifest: dict, *new_stages: str) -> list[str]:
    stages = [str(item) for item in manifest.get("completed_stages", [])]
    for stage in new_stages:
        if stage not in stages:
            stages.append(stage)
    return stages


def _repair_attempt_count(repair_history: list[dict]) -> int:
    attempts = [int(item.get("repair_attempt", 0)) for item in repair_history]
    attempts.extend(
        int(receipt.get("repair_attempt", 0))
        for item in repair_history
        if isinstance((receipt := item.get("repair_receipt")), dict)
    )
    return max(attempts, default=0)


def write_local_poc_review_evidence(
    bundle_dir: Path,
    *,
    deterministic_validation: dict,
    independent_review: dict,
    blind_quality_review: dict | None = None,
    factual_plan_review: dict | None = None,
    combined_review: dict | None = None,
    repair_history: list[dict],
    lifecycle_status: str,
    deterministic_validation_passed: bool,
    reviewer_standard_hash: str,
) -> None:
    """Write the reviewer boundary and advance the existing manifest in place."""

    allowed_statuses = {
        "AGENT_APPROVED",
        "AGENT_REVIEW_REJECTED",
        "README_ASSESSED",
        "DETERMINISTIC_VALIDATION_FAILED",
        "BLOCKED_FACT_CONFLICT",
        "BLOCKED_MISSING_EVIDENCE",
        "SYSTEM_FAILURE",
    }
    if lifecycle_status not in allowed_statuses:
        raise ValueError(f"unsupported local README review lifecycle status: {lifecycle_status}")
    agent_approved = lifecycle_status == "AGENT_APPROVED"
    review_dir = bundle_dir / "review"
    write_redacted_json(
        review_dir / "deterministic-validation.json",
        deterministic_validation,
    )
    write_redacted_json(
        review_dir / "independent-agent-review.json",
        independent_review,
    )
    if blind_quality_review is not None:
        write_redacted_json(review_dir / "blind-quality-review.json", blind_quality_review)
    if factual_plan_review is not None:
        write_redacted_json(review_dir / "factual-plan-review.json", factual_plan_review)
    if combined_review is not None:
        write_redacted_json(review_dir / "combined-review.json", combined_review)
    write_redacted_json(review_dir / "repair-history.json", repair_history)
    repair_attempts = _repair_attempt_count(repair_history)
    write_redacted_json(
        review_dir / "final-verdict.json",
        {
            "verdict": lifecycle_status,
            "agent_approved": agent_approved,
            "deterministic_validation_passed": deterministic_validation_passed,
            "repair_attempts": repair_attempts,
        },
    )

    manifest = _load_manifest(bundle_dir)
    if lifecycle_status == "DETERMINISTIC_VALIDATION_FAILED":
        completed = _completed_stages(manifest, "DETERMINISTIC_VALIDATION_FAILED")
    elif lifecycle_status == "README_ASSESSED":
        completed = _completed_stages(
            manifest,
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
            "AGENT_REVIEW_REJECTED",
            "REPAIRING",
            "README_ASSESSED",
        )
    else:
        completed = _completed_stages(
            manifest,
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
            lifecycle_status,
        )
    manifest.update(
        {
            "lifecycle_status": lifecycle_status,
            "reviewer_standard_hash": reviewer_standard_hash,
            "complete": False,
            "completed_stages": completed,
        }
    )
    write_local_poc_manifest(bundle_dir, manifest)
    refresh_sha256sums(bundle_dir)


def write_local_poc_no_op_evidence(
    bundle_dir: Path,
    *,
    candidate_hash: str,
    agentic_review_reused: bool,
) -> None:
    """Complete Gate-A repository evidence after an unchanged rerun."""

    from readme_agent.llm.call_ledger import current_llm_accounting_summary

    llm_summary = current_llm_accounting_summary()
    if llm_summary.status == "EXACT" and llm_summary.provider_call_count != 0:
        raise RuntimeError("unchanged README no-op made one or more new provider calls")
    write_redacted_json(
        bundle_dir / "review" / "no-op-proof.json",
        {
            "verdict": "NO_OP_PROVEN",
            "candidate_hash": candidate_hash,
            "patch_created": False,
            "duplicate_bundle_created": False,
            "agentic_review_reused": agentic_review_reused,
            "llm_accounting_status": llm_summary.status,
            "new_provider_call_count": llm_summary.provider_call_count,
            "new_cache_reuse_count": llm_summary.cache_reuse_count,
        },
    )
    manifest = _load_manifest(bundle_dir)
    manifest.update(
        {
            "lifecycle_status": "NO_OP_PROVEN",
            "complete": True,
            "completed_stages": _completed_stages(manifest, "NO_OP_PROVEN"),
        }
    )
    write_local_poc_manifest(bundle_dir, manifest)
    refresh_sha256sums(bundle_dir)
