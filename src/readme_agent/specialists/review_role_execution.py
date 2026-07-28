"""Execute one reviewer role with bounded finding-grounding correction."""

from __future__ import annotations

from typing import Protocol

from pydantic import ValidationError

from readme_agent.errors import LLMError
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.verification_prompts import build_role_grounding_retry_message
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewResultV1,
    FactualPlanReviewResultV1,
)
from readme_agent.specialists.review_finding_grounding import (
    FindingGroundingResultV1,
    grounding_retry_context,
    validate_review_findings,
)

_MAX_GROUNDING_ATTEMPTS = 2


class AnalysisClientLike(Protocol):
    """Minimal analysis-client seam used by independent reviewer roles."""

    def analyze(self, messages: list[dict]) -> AnalysisResult: ...


def _parse_role_result(
    role: str,
    result: AnalysisResult,
) -> BlindQualityReviewResultV1 | FactualPlanReviewResultV1:
    try:
        if role == "blind_quality":
            return BlindQualityReviewResultV1.model_validate(result.parsed)
        return FactualPlanReviewResultV1.model_validate(result.parsed)
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
) -> tuple[
    BlindQualityReviewResultV1 | FactualPlanReviewResultV1,
    list[dict],
    FindingGroundingResultV1,
]:
    """Run a reviewer and allow one bounded correction of invalid finding evidence."""

    history: list[dict] = []
    current_messages = list(messages)
    for attempt in range(1, _MAX_GROUNDING_ATTEMPTS + 1):
        analysis = client.analyze(current_messages)
        grounding: FindingGroundingResultV1 | None = None
        try:
            parsed = _parse_role_result(role, analysis)
            grounding = validate_review_findings(
                candidate_text=candidate_text,
                product_facts=product_facts,
                findings=parsed.findings,
            )
            errors = grounding.errors
        except LLMError as exc:
            parsed = None
            errors = [str(exc)]
        history.append(
            {
                "role": role,
                "attempt": attempt,
                "valid": not errors,
                "errors": errors,
                "validation_result": grounding.model_dump(mode="json") if grounding else None,
            }
        )
        if parsed is not None and grounding is not None and not errors:
            return parsed, history, grounding
        if attempt == _MAX_GROUNDING_ATTEMPTS:
            raise LLMError(f"{role} reviewer repeatedly returned ungrounded findings: {errors}")
        current_messages = [
            *current_messages,
            build_role_grounding_retry_message(
                prompt_id,
                grounding_retry_context(
                    errors=errors,
                    candidate_text=candidate_text,
                    product_facts=product_facts,
                ),
            ),
        ]
    raise AssertionError("grounding retry loop must return or raise")
