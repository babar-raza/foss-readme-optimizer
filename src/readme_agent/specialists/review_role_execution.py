"""Execute one reviewer role with bounded finding-grounding correction."""

from __future__ import annotations

from typing import Protocol

from pydantic import ValidationError

from readme_agent.errors import LLMError
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.verification_prompts import build_role_grounding_retry_message
from readme_agent.specialists.bounded_review_visitor_scope import (
    bounded_visitor_scope_errors,
)
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewResultV1,
    FactualPlanReviewResultV1,
)
from readme_agent.specialists.review_blind_reconciliation import (
    clear_irrelevant_mechanical_references,
    reconcile_deterministically_disproven_blind_findings,
)
from readme_agent.specialists.review_candidate_anchors import (
    CandidateReviewAnchorV1,
    bind_candidate_review_anchors,
    build_candidate_review_anchors,
    reconcile_unknown_candidate_review_anchors,
    unknown_candidate_review_anchor_ids,
)
from readme_agent.specialists.review_factual_reconciliation import (
    reconcile_candidate_spans,
    reconcile_supported_factual_evidence,
)
from readme_agent.specialists.review_finding_grounding import (
    GROUNDING_RETRY_CONTEXT_CONTRACT_VERSION,
    FindingGroundingResultV1,
    grounding_retry_context,
    validate_review_findings,
)
from readme_agent.specialists.review_role_normalization import normalize_redundant_role_fields

_MAX_GROUNDING_ATTEMPTS = 2
_MAX_BLIND_GROUNDING_ATTEMPTS = 3


class AnalysisClientLike(Protocol):
    """Minimal analysis-client seam used by independent reviewer roles."""

    def analyze(self, messages: list[dict]) -> AnalysisResult: ...


class BoundedBlindAnalysisClientLike(Protocol):
    """Optional client seam that enforces bounded criteria in the provider schema."""

    def analyze_bounded(
        self,
        messages: list[dict],
        allowed_quality_criteria: frozenset[str],
    ) -> AnalysisResult: ...


def _analyze_with_bounded_authority(
    *,
    role: str,
    client: AnalysisClientLike,
    messages: list[dict],
    allowed_quality_criteria: frozenset[str] | None,
) -> AnalysisResult:
    """Use a narrowed provider schema when the live blind client exposes it."""

    bounded_analyze = getattr(client, "analyze_bounded", None)
    if role == "blind_quality" and allowed_quality_criteria is not None and bounded_analyze:
        return bounded_analyze(messages, allowed_quality_criteria)
    return client.analyze(messages)


class GroundedRoleFailure(LLMError):
    """Reviewer failure that preserves every bounded grounding attempt."""

    def __init__(self, message: str, *, retry_history: tuple[dict, ...]) -> None:
        super().__init__(message)
        self.retry_history = retry_history


def _parse_role_result(
    role: str,
    result: AnalysisResult,
    *,
    candidate_anchors: tuple[CandidateReviewAnchorV1, ...] = (),
) -> BlindQualityReviewResultV1 | FactualPlanReviewResultV1:
    try:
        unknown = unknown_candidate_review_anchor_ids(result.parsed, candidate_anchors)
        if unknown:
            label = "blind README quality" if role == "blind_quality" else "factual README plan"
            raise LLMError(f"{label} review selected unknown anchors: {unknown}")
        anchored = bind_candidate_review_anchors(result.parsed, candidate_anchors)
        if role == "blind_quality":
            return BlindQualityReviewResultV1.model_validate(
                normalize_redundant_role_fields(
                    role,
                    anchored,
                )
            )
        return FactualPlanReviewResultV1.model_validate(
            normalize_redundant_role_fields(role, anchored)
        )
    except ValidationError as exc:
        label = "blind README quality" if role == "blind_quality" else "factual README plan"
        raise LLMError(f"{label} review violated its output contract: {exc}") from exc


def run_grounded_role(
    *,
    role: str,
    prompt_id: str,
    client: AnalysisClientLike,
    messages: list[dict],
    candidate_text: str,
    product_facts: dict | None,
    visitor_contract: dict | None = None,
    max_attempts_override: int | None = None,
    allowed_quality_criteria: frozenset[str] | None = None,
    allowed_mechanical_check_ids: frozenset[str] | None = None,
    failure_context: str | None = None,
    mechanical_candidate_text: str | None = None,
    mechanical_visitor_contract: dict | None = None,
) -> tuple[
    BlindQualityReviewResultV1 | FactualPlanReviewResultV1,
    list[dict],
    FindingGroundingResultV1,
]:
    """Run a reviewer and allow one bounded correction of invalid finding evidence."""

    history: list[dict] = []
    current_messages = list(messages)
    context_mode = "full_review_packet"
    candidate_anchors = build_candidate_review_anchors(candidate_text)
    if max_attempts_override is not None and max_attempts_override < 1:
        raise ValueError("max_attempts_override must be at least 1")
    max_attempts = max_attempts_override or (
        _MAX_BLIND_GROUNDING_ATTEMPTS if role == "blind_quality" else _MAX_GROUNDING_ATTEMPTS
    )
    for attempt in range(1, max_attempts + 1):
        analysis = _analyze_with_bounded_authority(
            role=role,
            client=client,
            messages=current_messages,
            allowed_quality_criteria=allowed_quality_criteria,
        )
        grounding: FindingGroundingResultV1 | None = None
        dismissed_finding_ids: tuple[str, ...] = ()
        reconciled_candidate_span_ids: tuple[str, ...] = ()
        reconciled_candidate_anchor_ids: tuple[str, ...] = ()
        reconciled_factual_polarity_ids: tuple[str, ...] = ()
        reconciled_factual_missing_ids: tuple[str, ...] = ()
        reconciled_irrelevant_mechanical_ids: tuple[str, ...] = ()
        original_errors: list[str] = []
        try:
            reconciled_value, reconciled_candidate_anchor_ids = (
                reconcile_unknown_candidate_review_anchors(
                    analysis.parsed,
                    candidate_anchors,
                    candidate_text,
                )
            )
            parsed = _parse_role_result(
                role,
                analysis.model_copy(update={"parsed": reconciled_value}),
                candidate_anchors=candidate_anchors,
            )
            parsed, reconciled_candidate_span_ids = reconcile_candidate_spans(
                parsed,
                candidate_text,
            )
            parsed, reconciled_factual_polarity_ids = reconcile_supported_factual_evidence(
                parsed,
                product_facts,
            )
            grounding = validate_review_findings(
                candidate_text=candidate_text,
                product_facts=product_facts,
                findings=parsed.findings,
                visitor_contract=visitor_contract,
                mechanical_candidate_text=mechanical_candidate_text,
                mechanical_visitor_contract=mechanical_visitor_contract,
            )
            errors = list(grounding.errors)
            if allowed_quality_criteria is not None:
                errors.extend(
                    bounded_visitor_scope_errors(
                        parsed.findings,
                        applicable_criteria=allowed_quality_criteria,
                        applicable_mechanical_check_ids=(
                            allowed_mechanical_check_ids or frozenset()
                        ),
                    )
                )
            original_errors = list(errors)
            parsed, reconciled_irrelevant_mechanical_ids = clear_irrelevant_mechanical_references(
                parsed, errors
            )
            if reconciled_irrelevant_mechanical_ids:
                grounding = validate_review_findings(
                    candidate_text=candidate_text,
                    product_facts=product_facts,
                    findings=parsed.findings,
                    visitor_contract=visitor_contract,
                    mechanical_candidate_text=mechanical_candidate_text,
                    mechanical_visitor_contract=mechanical_visitor_contract,
                )
                errors = list(grounding.errors)
                if allowed_quality_criteria is not None:
                    errors.extend(
                        bounded_visitor_scope_errors(
                            parsed.findings,
                            applicable_criteria=allowed_quality_criteria,
                            applicable_mechanical_check_ids=(
                                allowed_mechanical_check_ids or frozenset()
                            ),
                        )
                    )
            if errors:
                parsed, dismissed_finding_ids = (
                    reconcile_deterministically_disproven_blind_findings(
                        parsed,
                        errors,
                    )
                )
                if dismissed_finding_ids:
                    grounding = validate_review_findings(
                        candidate_text=candidate_text,
                        product_facts=product_facts,
                        findings=parsed.findings,
                        visitor_contract=visitor_contract,
                        mechanical_candidate_text=mechanical_candidate_text,
                        mechanical_visitor_contract=mechanical_visitor_contract,
                    )
                    errors = list(grounding.errors)
                    if allowed_quality_criteria is not None:
                        errors.extend(
                            bounded_visitor_scope_errors(
                                parsed.findings,
                                applicable_criteria=allowed_quality_criteria,
                                applicable_mechanical_check_ids=(
                                    allowed_mechanical_check_ids or frozenset()
                                ),
                            )
                        )
        except LLMError as exc:
            parsed = None
            errors = [str(exc)]
        invalid_finding_ids = {error.split(":", maxsplit=1)[0] for error in errors if ":" in error}
        history.append(
            {
                "role": role,
                "attempt": attempt,
                "context_mode": context_mode,
                "grounding_retry_context_contract_version": (
                    GROUNDING_RETRY_CONTEXT_CONTRACT_VERSION
                    if context_mode == "compact_grounding_retry"
                    else None
                ),
                "input_character_count": sum(
                    len(str(message.get("content", ""))) for message in current_messages
                ),
                "valid": not errors,
                "errors": errors,
                "validation_result": grounding.model_dump(mode="json") if grounding else None,
                "deterministically_dismissed_finding_ids": list(dismissed_finding_ids),
                "reconciled_candidate_span_ids": list(reconciled_candidate_span_ids),
                "reconciled_candidate_anchor_ids": list(reconciled_candidate_anchor_ids),
                "reconciled_factual_polarity_ids": list(reconciled_factual_polarity_ids),
                "reconciled_factual_missing_ids": list(reconciled_factual_missing_ids),
                "reconciled_irrelevant_mechanical_finding_ids": list(
                    reconciled_irrelevant_mechanical_ids
                ),
                "pre_normalization_errors": original_errors,
                "invalid_findings": [
                    {
                        "finding_id": finding.finding_id,
                        "criterion": finding.criterion,
                        "section": finding.section,
                        "claim": finding.claim,
                        "quoted_candidate_span": finding.quoted_candidate_span,
                        "candidate_anchor_id": finding.candidate_anchor_id,
                        "disposition": finding.disposition,
                        "fact_id": finding.fact_id,
                        "evidence_excerpt": finding.evidence_excerpt,
                        "evidence_location": finding.evidence_location,
                        "expected_polarity": finding.expected_polarity,
                        "observed_polarity": finding.observed_polarity,
                        "polarity_result": finding.polarity_result,
                        "required_repair": finding.required_repair,
                    }
                    for finding in parsed.findings
                    if finding.finding_id in invalid_finding_ids
                ]
                if parsed is not None
                else [],
            }
        )
        if parsed is not None and grounding is not None and not errors:
            return parsed, history, grounding
        if attempt == max_attempts:
            context_prefix = f"{failure_context}: " if failure_context else ""
            raise GroundedRoleFailure(
                f"{context_prefix}{role} reviewer repeatedly returned ungrounded findings: "
                f"{errors}",
                retry_history=tuple(history),
            )
        retry_message = build_role_grounding_retry_message(
            prompt_id,
            grounding_retry_context(
                errors=errors,
                candidate_text=candidate_text,
                product_facts=product_facts,
                findings=tuple(parsed.findings) if parsed is not None else (),
                visitor_contract=visitor_contract,
            ),
        )
        current_messages = [
            *[message for message in messages if message.get("role") == "system"],
            retry_message,
        ]
        context_mode = "compact_grounding_retry"
    raise AssertionError("grounding retry loop must return or raise")
