"""Execute one reviewer role with bounded finding-grounding correction."""

from __future__ import annotations

import re
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
_MAX_BLIND_GROUNDING_ATTEMPTS = 3


class AnalysisClientLike(Protocol):
    """Minimal analysis-client seam used by independent reviewer roles."""

    def analyze(self, messages: list[dict]) -> AnalysisResult: ...


class GroundedRoleFailure(LLMError):
    """Reviewer failure that preserves every bounded grounding attempt."""

    def __init__(self, message: str, *, retry_history: tuple[dict, ...]) -> None:
        super().__init__(message)
        self.retry_history = retry_history


def _normalized_finding_id(value: object) -> str:
    raw = str(value).strip().casefold()
    normalized = re.sub(r"[^a-z0-9_.-]+", "-", raw).strip("._-")
    if normalized and not normalized[0].isalpha():
        normalized = f"finding-{normalized}"
    return normalized or "finding"


def normalize_redundant_role_fields(role: str, value: object) -> object:
    """Derive rejection summaries from detailed findings without changing their verdict."""

    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    findings = normalized.get("findings")
    if isinstance(findings, list):
        normalized["findings"] = [
            (
                {
                    **item,
                    "finding_id": _normalized_finding_id(item["finding_id"]),
                }
                if isinstance(item, dict) and isinstance(item.get("finding_id"), str)
                else item
            )
            for item in findings
        ]
    if role != "blind_quality":
        return normalized
    if normalized.get("verdict") != "REJECT_REPAIRABLE":
        return normalized
    findings = normalized.get("findings")
    if not isinstance(findings, list) or not findings:
        return normalized
    valid_findings = [item for item in findings if isinstance(item, dict)]
    if len(valid_findings) != len(findings):
        return normalized
    normalized_findings = []
    for item in valid_findings:
        normalized_item = dict(item)
        if (
            normalized_item.get("disposition") == "requires_repair"
            and not str(normalized_item.get("required_repair", "")).strip()
        ):
            section = str(normalized_item.get("section", "README section")).strip()
            claim = str(normalized_item.get("claim", "visible presentation defect")).strip()
            normalized_item["required_repair"] = (
                f"Repair the quoted {section} presentation defect: {claim}"
            )
        normalized_findings.append(normalized_item)
    normalized["findings"] = normalized_findings
    normalized["failed_criteria"] = list(
        dict.fromkeys(
            str(item["criterion"])
            for item in normalized_findings
            if str(item.get("criterion", "")).strip()
        )
    )
    normalized["sections_affected"] = list(
        dict.fromkeys(
            str(item["section"])
            for item in normalized_findings
            if str(item.get("section", "")).strip()
        )
    )
    normalized["required_repair"] = " ".join(
        dict.fromkeys(
            str(item["required_repair"]).strip()
            for item in normalized_findings
            if str(item.get("required_repair", "")).strip()
        )
    )
    return normalized


def _parse_role_result(
    role: str,
    result: AnalysisResult,
) -> BlindQualityReviewResultV1 | FactualPlanReviewResultV1:
    try:
        if role == "blind_quality":
            return BlindQualityReviewResultV1.model_validate(
                normalize_redundant_role_fields(role, result.parsed)
            )
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
    visitor_contract: dict | None = None,
) -> tuple[
    BlindQualityReviewResultV1 | FactualPlanReviewResultV1,
    list[dict],
    FindingGroundingResultV1,
]:
    """Run a reviewer and allow one bounded correction of invalid finding evidence."""

    history: list[dict] = []
    current_messages = list(messages)
    max_attempts = (
        _MAX_BLIND_GROUNDING_ATTEMPTS if role == "blind_quality" else _MAX_GROUNDING_ATTEMPTS
    )
    for attempt in range(1, max_attempts + 1):
        analysis = client.analyze(current_messages)
        grounding: FindingGroundingResultV1 | None = None
        try:
            parsed = _parse_role_result(role, analysis)
            grounding = validate_review_findings(
                candidate_text=candidate_text,
                product_facts=product_facts,
                findings=parsed.findings,
                visitor_contract=visitor_contract,
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
        if attempt == max_attempts:
            raise GroundedRoleFailure(
                f"{role} reviewer repeatedly returned ungrounded findings: {errors}",
                retry_history=tuple(history),
            )
        current_messages = [
            *messages,
            build_role_grounding_retry_message(
                prompt_id,
                grounding_retry_context(
                    errors=errors,
                    candidate_text=candidate_text,
                    product_facts=product_facts,
                    findings=tuple(parsed.findings) if parsed is not None else (),
                    visitor_contract=visitor_contract,
                ),
            ),
        ]
    raise AssertionError("grounding retry loop must return or raise")
