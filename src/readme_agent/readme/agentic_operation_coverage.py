"""Fail closed when an actionable agentic section decision has no bounded edit."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from readme_agent.errors import LLMError
from readme_agent.readme.assessment import AssessmentDisposition, ReadmeAssessmentV1
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1

_ACTIONABLE = {"add", "repair", "remove_update", "replace_generic", "rewrite"}


class SectionDecision(Protocol):
    section_id: str
    disposition: AssessmentDisposition


def validate_agentic_operation_coverage(
    assessment: ReadmeAssessmentV1,
    decisions: Iterable[SectionDecision],
    operations: list[ReadmeDocumentOperationV1],
) -> None:
    """Require each actionable decision to be realized by an operation in its source span."""

    sections = {section.section_id: section for section in assessment.sections}
    missing: list[str] = []
    for decision in decisions:
        if decision.disposition not in _ACTIONABLE:
            continue
        section = sections[decision.section_id]
        if not any(
            _operation_covers_decision(
                operation,
                section.source_byte_start,
                section.source_byte_end,
                decision.disposition,
            )
            for operation in operations
        ):
            missing.append(f"{decision.section_id}:{decision.disposition}")
    if missing:
        raise LLMError(
            "agentic composition has actionable decisions without bounded operations: "
            f"{sorted(missing)}"
        )


def _operation_covers_decision(
    operation: ReadmeDocumentOperationV1,
    section_start: int,
    section_end: int,
    disposition: AssessmentDisposition,
) -> bool:
    if disposition in {
        "remove_update",
        "replace_generic",
        "rewrite",
    } and operation.operation not in {
        "remove",
        "replace",
    }:
        return False
    if operation.source_byte_start == operation.source_byte_end:
        return section_start <= operation.source_byte_start <= section_end
    return operation.source_byte_start < section_end and section_start < operation.source_byte_end
