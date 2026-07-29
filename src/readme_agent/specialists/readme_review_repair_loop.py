"""Control bounded README repair, delta proof, and independent rereview."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Protocol

from readme_agent.llm import prompt_registry
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.specialists.independent_readme_review import (
    MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS,
    IndependentReadmeReviewResultV1,
    RepairLoopOutcomeV1,
    independent_render_context,
    run_independent_readme_review,
)
from readme_agent.specialists.readme_repair_contracts import RepairAttemptReceiptV1
from readme_agent.specialists.readme_repair_validation import (
    build_repair_attempt_receipt,
    finalize_repair_receipt,
)
from readme_agent.specialists.readme_review_repair_state import (
    build_repair_backlog_finding,
    record_repaired_candidate_state,
    reroute_unchanged_repair,
)
from readme_agent.state.backend import StateBackend
from readme_agent.state.readme_poc_lifecycle import transition_readme_poc_status

_BLOCKED_VERDICTS = {
    "BLOCKED_FACT_CONFLICT",
    "BLOCKED_MISSING_EVIDENCE",
    "SYSTEM_FAILURE",
}
_OBSERVED_BY = "independent_readme_review"


class AnalysisClientLike(Protocol):
    """Compatibility client seam for the historical single-review route."""

    def analyze(self, messages: list[dict]) -> AnalysisResult: ...


def _promote_repaired_context(context: dict) -> dict:
    promote = context.pop("promote_repaired_context", None)
    if promote is None:
        return context
    if not callable(promote):
        raise RuntimeError("repair context promotion seam is not callable")
    promoted = promote()
    if promoted:
        context.update(promoted)
    return context


def run_independent_review_with_repair_loop(
    org_repo: str,
    backend: StateBackend | None,
    initial_context: dict,
    *,
    client: AnalysisClientLike | None = None,
    regenerate_context: Callable[[IndependentReadmeReviewResultV1, int], dict] | None = None,
    review_runner: (Callable[[str, dict, int], IndependentReadmeReviewResultV1] | None) = None,
    reviewer_standard_hash: str | None = None,
    review_observed_by: str = _OBSERVED_BY,
) -> RepairLoopOutcomeV1:
    """Repair only relevant candidate operations and rereview only after delta proof."""

    regenerate = regenerate_context or (
        lambda _review, _attempt: independent_render_context(
            org_repo,
            force_regenerate=True,
            product_facts_v2=initial_context.get("product_facts_v2"),
        )
    )
    context = initial_context
    attempts = 0
    reviewer_call_count = 0
    repair_history: list[dict] = []
    pending_receipt_index: int | None = None
    standard_hash = reviewer_standard_hash or prompt_registry.prompt_hash(
        "independent_readme_review"
    )
    while True:
        if review_runner is None:
            review = run_independent_readme_review(
                org_repo,
                context["original_text"],
                context["final_text"],
                context["presentation_plan"],
                context["deterministic_validation_result"],
                client=client,
                backend=backend,
                repair_attempt=attempts,
                product_facts_v2=context.get("product_facts_v2"),
            )
        else:
            review = review_runner(org_repo, context, attempts)
        reviewer_call_count += 1
        if pending_receipt_index is not None:
            prior_receipt = RepairAttemptReceiptV1.model_validate(
                repair_history[pending_receipt_index]["repair_receipt"]
            )
            repair_history[pending_receipt_index]["repair_receipt"] = finalize_repair_receipt(
                prior_receipt,
                rereview_verdict=review.verdict,
                reviewer_call_count=reviewer_call_count,
            ).model_dump(mode="json")
            pending_receipt_index = None

        review_record = {
            "review_pass": len([item for item in repair_history if item.get("review") is not None])
            + 1,
            "repair_attempt": attempts,
            "candidate_sha256": _candidate_hash(context),
            "review": review.model_dump(mode="json"),
            "deterministic_validation": context["deterministic_validation_result"],
            "evidence_refs": list(context.get("evidence_refs", [])),
            "reviewer_call_count": reviewer_call_count,
        }
        repair_history.append(review_record)

        if review.verdict == "ACCEPT":
            return RepairLoopOutcomeV1(
                outcome_kind="accepted",
                final_review=review,
                attempts=attempts,
                repair_history=repair_history,
                final_context=context,
                review_call_count=reviewer_call_count,
            )
        if review.verdict in _BLOCKED_VERDICTS:
            return RepairLoopOutcomeV1(
                outcome_kind="blocked",
                final_review=review,
                attempts=attempts,
                repair_history=repair_history,
                final_context=context,
                review_call_count=reviewer_call_count,
            )
        if attempts >= MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS:
            return RepairLoopOutcomeV1(
                outcome_kind="repair_exhausted",
                final_review=review,
                attempts=attempts,
                escalation=build_repair_backlog_finding(org_repo, review, attempts),
                repair_history=repair_history,
                final_context=context,
                review_call_count=reviewer_call_count,
            )

        while attempts < MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS:
            next_attempt = attempts + 1
            if backend is not None:
                transition_readme_poc_status(
                    backend,
                    org_repo,
                    "REPAIRING",
                    observed_by=review_observed_by,
                    reason=(
                        f"entering repair attempt {next_attempt}/"
                        f"{MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS}: {review.required_repair}"
                    ),
                    evidence_refs=list(review.failed_criteria),
                )
            repaired_context = regenerate(review, next_attempt)
            attempts = next_attempt
            receipt = build_repair_attempt_receipt(
                prior_context=context,
                repaired_context=repaired_context,
                review=review,
                repair_attempt=attempts,
                reviewer_call_count=reviewer_call_count,
            )
            review_record["repair_receipt"] = receipt.model_dump(mode="json")
            if not receipt.rereview_authorized:
                escalation = reroute_unchanged_repair(
                    org_repo=org_repo,
                    backend=backend,
                    review=review,
                    receipt=receipt,
                    observed_by=review_observed_by,
                )
                return RepairLoopOutcomeV1(
                    outcome_kind="repair_rerouted",
                    final_review=review,
                    attempts=attempts,
                    escalation=escalation,
                    repair_history=repair_history,
                    final_context=context,
                    review_call_count=reviewer_call_count,
                )

            context = _promote_repaired_context(repaired_context)
            deterministic_passed = context.get("deterministic_validation_passed")
            if deterministic_passed is None:
                deterministic_passed = (
                    context.get("deterministic_validation_result", {}).get("verdict") == "accept"
                )
            if backend is not None:
                record_repaired_candidate_state(
                    backend=backend,
                    org_repo=org_repo,
                    context=context,
                    attempts=attempts,
                    deterministic_passed=bool(deterministic_passed),
                    observed_by=review_observed_by,
                    standard_hash=standard_hash,
                )
            if deterministic_passed:
                pending_receipt_index = len(repair_history) - 1
                break
            repair_history.append(
                {
                    "review_pass": len(
                        [item for item in repair_history if item.get("review") is not None]
                    )
                    + 1,
                    "repair_attempt": attempts,
                    "candidate_sha256": _candidate_hash(context),
                    "review": None,
                    "deterministic_validation": context.get("deterministic_validation_result", {}),
                    "evidence_refs": list(context.get("evidence_refs", [])),
                    "reviewer_call_count": reviewer_call_count,
                    "repair_receipt": receipt.model_dump(mode="json"),
                }
            )
            if attempts >= MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS:
                escalation = build_repair_backlog_finding(org_repo, review, attempts)
                escalation["reason"] = (
                    "independent_readme_review: repaired candidate still failed "
                    f"deterministic validation after {attempts} attempts"
                )
                return RepairLoopOutcomeV1(
                    outcome_kind="repair_exhausted",
                    final_review=review,
                    attempts=attempts,
                    escalation=escalation,
                    repair_history=repair_history,
                    final_context=context,
                    review_call_count=reviewer_call_count,
                )


def _candidate_hash(context: dict) -> str:
    return hashlib.sha256(str(context["final_text"]).encode("utf-8")).hexdigest()
