"""Turn unresolved source-section assessments into bounded withholding operations."""

from __future__ import annotations

from readme_agent.readme.assessment import ReadmeAssessmentV1, ReadmeSectionAssessmentV1
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext


def _outermost_investigations(
    assessment: ReadmeAssessmentV1,
) -> list[ReadmeSectionAssessmentV1]:
    candidates = sorted(
        (
            section
            for section in assessment.sections
            if section.disposition == "investigate"
            and section.source_byte_start < section.source_byte_end
        ),
        key=lambda section: (
            section.source_byte_start,
            -(section.source_byte_end - section.source_byte_start),
        ),
    )
    selected: list[ReadmeSectionAssessmentV1] = []
    for section in candidates:
        if any(
            parent.source_byte_start <= section.source_byte_start
            and section.source_byte_end <= parent.source_byte_end
            for parent in selected
        ):
            continue
        selected.append(section)
    return selected


def build_unresolved_section_operations(
    context: DocumentRenderContext,
    assessment: ReadmeAssessmentV1,
) -> list[ReadmeDocumentOperationV1]:
    """Withhold source sections whose dependent truth is unresolved."""

    return [
        build_operation(
            operation_id=f"readme.unresolved.withhold:{index}",
            operation="remove",
            source=context.source,
            start=section.source_byte_start,
            end=section.source_byte_end,
            replacement="",
            fact_ids=[],
            treatment="presentation_policy_correction",
            rationale=(
                f"Withhold the source-bound {section.heading!r} section because its assessment "
                "requires unresolved evidence. Preserve its exact bytes and uncertainty in the "
                "assessment and evidence bundle instead of presenting it as verified fact."
            ),
        )
        for index, section in enumerate(_outermost_investigations(assessment), start=1)
    ]


def remove_operations_overlapping_withheld_sections(
    operations: list[ReadmeDocumentOperationV1],
    withheld: list[ReadmeDocumentOperationV1],
) -> list[ReadmeDocumentOperationV1]:
    """Give a withholding decision exclusive ownership of its immutable source span."""

    def overlaps_withheld(operation: ReadmeDocumentOperationV1) -> bool:
        for removal in withheld:
            if operation.source_byte_start == operation.source_byte_end:
                if (
                    removal.source_byte_start
                    < operation.source_byte_start
                    < removal.source_byte_end
                ):
                    return True
                continue
            if (
                operation.source_byte_start < removal.source_byte_end
                and removal.source_byte_start < operation.source_byte_end
            ):
                return True
        return False

    return [operation for operation in operations if not overlaps_withheld(operation)]
