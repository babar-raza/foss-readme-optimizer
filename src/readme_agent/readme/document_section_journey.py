"""Normalize the visible core section journey without losing source content."""

from __future__ import annotations

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_structure import Heading

_CAPABILITY_HEADINGS = {
    "capabilities",
    "currently available features",
    "features",
    "key capabilities",
}


def _overlaps(
    start: int,
    end: int,
    operations: list[ReadmeDocumentOperationV1],
) -> bool:
    return any(
        operation.source_byte_start < end and start < operation.source_byte_end
        for operation in operations
    )


def _is_why_heading(heading: Heading) -> bool:
    return heading.level == 2 and heading.title.strip().casefold().startswith("why ")


def _is_capability_heading(heading: Heading) -> bool:
    return heading.level == 2 and heading.title.strip().casefold() in _CAPABILITY_HEADINGS


def _body(context: DocumentRenderContext, heading: Heading) -> str:
    return context.inner_text[heading.heading_end : heading.section_end].strip()


def _details(title: str, body: str) -> str:
    return f"<details>\n<summary>{title.strip()}</summary>\n\n{body}\n\n</details>"


def _generated_capabilities(
    context: DocumentRenderContext,
) -> tuple[str, list[str]]:
    view = visitor_fact_render_view(context.facts, "product.capabilities")
    labels = list(view.phrases) if view is not None else []
    fact_ids = list(view.citation_fact_ids) if view is not None else []
    unique_labels = list(dict.fromkeys(label.strip() for label in labels if label.strip()))
    return "\n".join(f"- {label}" for label in unique_labels), list(dict.fromkeys(fact_ids))


def _insertion_offset(context: DocumentRenderContext) -> int:
    at_a_glance = context.h2("at a glance")
    if at_a_glance is not None:
        return context.byte_offset(at_a_glance.section_end)
    first_h2 = next((heading for heading in context.headings if heading.level == 2), None)
    return context.byte_offset(first_h2.start) if first_h2 is not None else len(context.source)


def build_core_section_journey_operations(
    context: DocumentRenderContext,
    existing_operations: list[ReadmeDocumentOperationV1],
) -> list[ReadmeDocumentOperationV1]:
    """Place one loss-bounded Key capabilities section after the generated overview."""

    capability_sections = [
        heading for heading in context.headings if _is_capability_heading(heading)
    ]
    why_sections = [heading for heading in context.headings if _is_why_heading(heading)]
    selected_sections = [*capability_sections, *why_sections]
    insertion = _insertion_offset(context)
    if (
        len(capability_sections) == 1
        and not why_sections
        and context.byte_offset(capability_sections[0].start) == insertion
        and capability_sections[0].title.strip().casefold() == "key capabilities"
    ):
        return []
    spans = [
        (context.byte_offset(heading.start), context.byte_offset(heading.section_end))
        for heading in selected_sections
    ]
    if any(_overlaps(start, end, existing_operations) for start, end in spans):
        return []

    fact_ids: list[str] = []
    if capability_sections:
        primary = capability_sections[0]
        visible_body = _body(context, primary)
        disclosures = [
            _details(heading.title, _body(context, heading))
            for heading in [*why_sections, *capability_sections[1:]]
            if _body(context, heading)
        ]
    elif why_sections:
        primary = why_sections[0]
        visible_body = _body(context, primary)
        disclosures = [
            _details(heading.title, _body(context, heading))
            for heading in why_sections[1:]
            if _body(context, heading)
        ]
    else:
        visible_body, fact_ids = _generated_capabilities(context)
        disclosures = []
    if not visible_body:
        return []

    content = "\n\n".join([visible_body, *disclosures])
    replacement = f"## Key capabilities\n\n{content}\n\n"
    operations = [
        build_operation(
            operation_id="readme.journey.key-capabilities",
            operation="insert_before",
            source=context.source,
            start=insertion,
            end=insertion,
            replacement=replacement,
            fact_ids=fact_ids,
            treatment=("presentation_policy_correction" if selected_sections else "additive"),
            rationale=(
                "Place one repository-specific Key capabilities section in the accepted core "
                "journey while retaining all source section content."
            ),
        )
    ]
    for heading, (start, end) in zip(selected_sections, spans, strict=True):
        operations.append(
            build_operation(
                operation_id=f"readme.journey.remove-source-capabilities:{start}",
                operation="remove",
                source=context.source,
                start=start,
                end=end,
                replacement="",
                fact_ids=[],
                treatment="presentation_policy_correction",
                rationale=(
                    f"Move the exact {heading.title!r} content into the canonical Key "
                    "capabilities position."
                ),
            )
        )
    return operations
