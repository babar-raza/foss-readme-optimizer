"""Persist README repair outcomes and agent-fixable reroutes."""

from __future__ import annotations

from readme_agent.specialists.independent_readme_review import (
    MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS,
    IndependentReadmeReviewResultV1,
)
from readme_agent.specialists.readme_repair_contracts import RepairAttemptReceiptV1
from readme_agent.state.backend import StateBackend
from readme_agent.state.readme_poc_lifecycle import (
    record_deterministic_validation_failure,
    transition_readme_poc_status,
)


def build_repair_backlog_finding(
    org_repo: str,
    review: IndependentReadmeReviewResultV1,
    attempts: int,
) -> dict:
    """Create an explicit agent-fixable finding when bounded repair is exhausted."""

    return {
        "repository": org_repo,
        "status": "AGENT_REVIEW_REJECTED",
        "reason": (
            "independent_readme_review: repair attempts exhausted "
            f"({attempts}/{MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS}), still {review.verdict}"
        ),
        "actionable": True,
        "blocked_category": "agent_fixable",
        "repair_attempts": attempts,
        "verdict": review.verdict,
        "failed_criteria": list(review.failed_criteria),
        "required_repair": review.required_repair,
    }


def reroute_unchanged_repair(
    *,
    org_repo: str,
    backend: StateBackend | None,
    review: IndependentReadmeReviewResultV1,
    receipt: RepairAttemptReceiptV1,
    observed_by: str,
) -> dict:
    """Reopen composition when a repair cannot prove a relevant operation change."""

    reason = (
        "agent_fixable: reviewer-directed repair did not materially change every responsible "
        f"span/operation; before={receipt.before_candidate_sha256} "
        f"after={receipt.after_candidate_sha256}; "
        f"unresolved={','.join(receipt.unresolved_finding_ids)}"
    )
    if backend is not None:
        transition_readme_poc_status(
            backend,
            org_repo,
            "README_ASSESSED",
            observed_by=observed_by,
            reason=reason,
            evidence_refs=receipt.unresolved_finding_ids,
        )
    return {
        "repository": org_repo,
        "status": "README_ASSESSED",
        "reason": reason,
        "actionable": True,
        "blocked_category": "agent_fixable",
        "repair_attempts": receipt.repair_attempt,
        "verdict": review.verdict,
        "failed_criteria": list(review.failed_criteria),
        "required_repair": review.required_repair,
        "repair_receipt": receipt.model_dump(mode="json"),
    }


def record_repaired_candidate_state(
    *,
    backend: StateBackend,
    org_repo: str,
    context: dict,
    attempts: int,
    deterministic_passed: bool,
    observed_by: str,
    standard_hash: str,
) -> None:
    """Advance a materially changed repair through deterministic validation."""

    current = backend.load(org_repo)
    lifecycle = current.readme_poc_lifecycle if current is not None else None
    if lifecycle is None:
        raise RuntimeError("README-POC lifecycle disappeared during repair")
    if lifecycle.status == "REPAIRING":
        transition_readme_poc_status(
            backend,
            org_repo,
            "CANDIDATE_GENERATED",
            observed_by=observed_by,
            reason=(
                f"candidate regenerated for repair attempt {attempts}/"
                f"{MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS}"
            ),
            evidence_refs=list(context.get("evidence_refs", [])),
        )
    if not deterministic_passed:
        record_deterministic_validation_failure(
            backend,
            org_repo,
            observed_by=observed_by,
            reason="repaired candidate failed deterministic validation",
            evidence_refs=list(context.get("evidence_refs", [])),
        )
        return
    transition_readme_poc_status(
        backend,
        org_repo,
        "DETERMINISTIC_VALIDATED",
        observed_by=observed_by,
        reason="repaired candidate passed all deterministic validation gates",
        evidence_refs=list(context.get("evidence_refs", [])),
    )
    transition_readme_poc_status(
        backend,
        org_repo,
        "AGENT_REVIEWING",
        observed_by=observed_by,
        reason="independent review restarted after material repair validation",
        evidence_refs=list(context.get("evidence_refs", [])),
        reviewer_standard_hash=standard_hash,
    )
