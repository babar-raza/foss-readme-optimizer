"""Ground trusted fidelity-review output in exact source and candidate spans."""

from __future__ import annotations

import json

from pydantic import ValidationError

from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.verification_prompts import build_role_grounding_retry_message
from readme_agent.specialists.review_role_execution import AnalysisClientLike
from readme_agent.specialists.trusted_transform_review_models import (
    TrustedFidelityReviewResultV1,
)

_MAX_ATTEMPTS = 2
_PROMPT_ID = "trusted_readme_fidelity_review"


def validate_trusted_fidelity_result(
    result: TrustedFidelityReviewResultV1,
    graph: TrustedReadmeFactGraphV1,
    candidate_text: str,
) -> tuple[str, ...]:
    """Reject incomplete inventories, invented quotes, and wrong verdict direction."""

    if result.verdict == "SYSTEM_FAILURE":
        return ()
    errors: list[str] = []
    facts = {fact.fact_id: fact for fact in graph.inherited_facts}
    check_ids = [item.fact_id for item in result.source_checks]
    if len(check_ids) != len(set(check_ids)):
        errors.append("duplicate inherited fact checks")
    if set(check_ids) != set(facts):
        missing = sorted(set(facts) - set(check_ids))
        unknown = sorted(set(check_ids) - set(facts))
        errors.append(f"source-check inventory mismatch: missing={missing}, unknown={unknown}")
    for check in result.source_checks:
        fact = facts.get(check.fact_id)
        if fact is None:
            continue
        if check.source_quote not in fact.value:
            errors.append(f"{check.fact_id}: source quote is absent from inherited source")
        if check.candidate_quote and check.candidate_quote not in candidate_text:
            errors.append(f"{check.fact_id}: candidate quote is absent")
    for addition in result.unsupported_additions:
        if addition.quoted_candidate_span not in candidate_text:
            errors.append(f"{addition.finding_id}: candidate quote is absent")
    defects = any(item.outcome == "lost_or_distorted" for item in result.source_checks) or bool(
        result.unsupported_additions
    )
    if result.verdict == "ACCEPT" and defects:
        errors.append("fidelity ACCEPT contradicts grounded defects")
    if result.verdict == "REJECT_REPAIRABLE" and not defects:
        errors.append("fidelity rejection has no grounded defect")
    return tuple(errors)


def run_trusted_fidelity_role(
    *,
    client: AnalysisClientLike,
    messages: list[dict],
    graph: TrustedReadmeFactGraphV1,
    candidate_text: str,
) -> tuple[TrustedFidelityReviewResultV1, tuple[dict, ...]]:
    """Run one fidelity role with one bounded deterministic-grounding correction."""

    current_messages = list(messages)
    history: list[dict] = []
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        analysis: AnalysisResult = client.analyze(current_messages)
        try:
            parsed = TrustedFidelityReviewResultV1.model_validate(analysis.parsed)
            errors = validate_trusted_fidelity_result(parsed, graph, candidate_text)
        except ValidationError as exc:
            parsed = None
            errors = (f"trusted fidelity output contract violation: {exc}",)
        history.append(
            {
                "role": "inheritance_fidelity",
                "attempt": attempt,
                "valid": not errors,
                "errors": list(errors),
            }
        )
        if parsed is not None and not errors:
            return parsed, tuple(history)
        if attempt == _MAX_ATTEMPTS:
            raise LLMError(
                f"inheritance fidelity reviewer repeatedly returned ungrounded output: {errors}"
            )
        reconciliation = json.dumps(
            {
                "validation_errors": errors,
                "required_fact_ids": [fact.fact_id for fact in graph.inherited_facts],
                "candidate_length": len(candidate_text.encode("utf-8")),
            },
            sort_keys=True,
        )
        current_messages = [
            *current_messages,
            build_role_grounding_retry_message(_PROMPT_ID, reconciliation),
        ]
    raise AssertionError("trusted fidelity retry loop must return or raise")
