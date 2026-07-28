"""Plan bounded README limitation operations from verified constraints."""

from __future__ import annotations

from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_templates import (
    accepted_fact,
    limitations_text,
    missing_limitation_constraints_text,
)


def build_limitation_operations(
    context: DocumentRenderContext,
) -> list[ReadmeDocumentOperationV1]:
    """Add or complete a limitations section without replacing maintainer prose."""

    heading = context.h2("limitations", "known limitations", "known limits")
    verified_limitations = limitations_text(context.facts)
    if not verified_limitations:
        return []
    limitation = accepted_fact(context.facts, "product.limitations")
    if heading is None:
        byte_offset = len(context.source)
        separator = (
            ""
            if context.inner_text.endswith("\n\n")
            else "\n"
            if context.inner_text.endswith("\n")
            else "\n\n"
        )
        return [
            build_operation(
                operation_id="readme.limitations.add-verified",
                operation="insert_after",
                source=context.source,
                start=byte_offset,
                end=byte_offset,
                replacement=separator + verified_limitations + "\n",
                fact_ids=[limitation.fact_id] if limitation is not None else [],
                treatment="additive",
                rationale=(
                    "Expose repository-verified limitations instead of silently presenting "
                    "incomplete capability coverage."
                ),
            )
        ]
    section_text = context.inner_text[heading.heading_end : heading.section_end]
    missing_constraints = missing_limitation_constraints_text(context.facts, section_text)
    if not missing_constraints:
        return []
    byte_offset = context.byte_offset(heading.section_end)
    separator = (
        "" if section_text.endswith("\n\n") else "\n" if section_text.endswith("\n") else "\n\n"
    )
    return [
        build_operation(
            operation_id="readme.limitations.complete-verified",
            operation="insert_before",
            source=context.source,
            start=byte_offset,
            end=byte_offset,
            replacement=separator + missing_constraints + "\n\n",
            fact_ids=[limitation.fact_id] if limitation is not None else [],
            treatment="additive",
            rationale=(
                "Complete the existing limitations section with exact repository-verified "
                "constraints while preserving its maintainer-authored content."
            ),
        )
    ]
