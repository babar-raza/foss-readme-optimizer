"""Normalize the visible core journey around accepted, fact-backed capabilities."""

from __future__ import annotations

from markdown_it import MarkdownIt

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_structure import Heading
from readme_agent.readme.header_visual_models import ReadmeHeaderVisualV1

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


def _generated_capabilities(
    context: DocumentRenderContext,
    header_visuals: ReadmeHeaderVisualV1,
) -> tuple[str, list[str]]:
    capability_nodes = [node for node in header_visuals.diagram_nodes if node.role == "capability"]
    if capability_nodes:
        labels = list(dict.fromkeys(node.label.strip() for node in capability_nodes))
        fact_ids = list(
            dict.fromkeys(fact_id for node in capability_nodes for fact_id in node.fact_ids)
        )
        return "\n".join(f"- {label}" for label in labels), fact_ids

    view = visitor_fact_render_view(context.facts, "product.capabilities")
    labels = list(view.phrases) if view is not None else []
    fact_ids = list(view.citation_fact_ids) if view is not None else []
    unique_labels = list(dict.fromkeys(label.strip() for label in labels if label.strip()))
    return "\n".join(f"- {label}" for label in unique_labels), list(dict.fromkeys(fact_ids))


def _non_list_source_context(body: str) -> str:
    """Retain visible non-list source context while replacing unverified claim inventories."""

    lines = body.splitlines(keepends=True)
    omitted: set[int] = set()
    for token in MarkdownIt("commonmark").parse(body):
        if (
            token.type in {"bullet_list_open", "ordered_list_open"}
            and token.level == 0
            and token.map is not None
        ):
            start, end = token.map
            omitted.update(range(start, end))
    retained = "".join(line for index, line in enumerate(lines) if index not in omitted)
    return retained.strip()


def _source_context_blocks(
    context: DocumentRenderContext,
    sections: list[Heading],
) -> list[str]:
    blocks: list[str] = []
    for heading in sections:
        retained = _non_list_source_context(_body(context, heading))
        if not retained:
            continue
        title = heading.title.strip()
        if title.casefold() == "key capabilities":
            title = "Additional capability context"
        blocks.append(f"### {title}\n\n{retained}")
    return blocks


def _insertion_offset(context: DocumentRenderContext) -> int:
    at_a_glance = context.h2("at a glance")
    if at_a_glance is not None:
        return context.byte_offset(at_a_glance.section_end)
    first_h2 = next((heading for heading in context.headings if heading.level == 2), None)
    return context.byte_offset(first_h2.start) if first_h2 is not None else len(context.source)


def build_core_section_journey_operations(
    context: DocumentRenderContext,
    existing_operations: list[ReadmeDocumentOperationV1],
    header_visuals: ReadmeHeaderVisualV1,
) -> list[ReadmeDocumentOperationV1]:
    """Place one open, fact-backed Key capabilities section after the overview."""

    capability_sections = [
        heading for heading in context.headings if _is_capability_heading(heading)
    ]
    why_sections = [heading for heading in context.headings if _is_why_heading(heading)]
    selected_sections = [*capability_sections, *why_sections]
    insertion = _insertion_offset(context)
    spans = [
        (context.byte_offset(heading.start), context.byte_offset(heading.section_end))
        for heading in selected_sections
    ]
    if any(_overlaps(start, end, existing_operations) for start, end in spans):
        return []

    visible_body, fact_ids = _generated_capabilities(context, header_visuals)
    if not visible_body:
        return []

    if (
        len(capability_sections) == 1
        and not why_sections
        and context.byte_offset(capability_sections[0].start) == insertion
        and capability_sections[0].title.strip().casefold() == "key capabilities"
        and (
            _body(context, capability_sections[0]) == visible_body
            or _body(context, capability_sections[0]).startswith(f"{visible_body}\n\n")
        )
    ):
        return []
    source_context = _source_context_blocks(context, selected_sections)
    content = "\n\n".join([visible_body, *source_context])
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
                "Place one open, repository-specific Key capabilities list backed by accepted "
                "diagram facts while retaining useful non-list source context visibly."
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
                fact_ids=fact_ids,
                treatment="presentation_policy_correction",
                rationale=(
                    f"Replace the inherited {heading.title!r} claim inventory with the "
                    "accepted fact-backed capability list and retain its non-list context."
                ),
            )
        )
    return operations
