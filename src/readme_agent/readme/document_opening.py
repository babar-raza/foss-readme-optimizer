"""Plan product-first README opening and overview operations."""

from __future__ import annotations

import re

from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_overview import overview_text
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_templates import (
    accepted_fact,
)
from readme_agent.readme.fact_grounding import literal_fact_ids
from readme_agent.readme.header_visual_models import ReadmeHeaderVisualV1
from readme_agent.readme.presentation_report import product_explanation_offset

_PROMOTIONAL_CALLOUT = re.compile(
    r"(?m)^>[^\n]*(?:products\.aspose\.org)[^\n]*(?:products\.aspose\.com)[^\n]*\n(?:\n)?",
    re.IGNORECASE,
)
_BADGE_LINE = re.compile(
    r"(?im)^(?![ \t]*<!--)[^\n]*(?:!\[[^\]]*\]\([^)]*(?:shields\.io|badge|actions/workflows)[^)]*\)"
    r"[^\n]*)\n?"
)


def build_opening_operations(
    context: DocumentRenderContext,
    agentic_plan: ReadmeAgenticCompositionPlanV1 | None,
    visual_plan: ReadmeHeaderVisualV1,
    *,
    insertion_byte_offset: int | None = None,
) -> list[ReadmeDocumentOperationV1]:
    """Add missing overview, acquisition, and minimal-example sections as one operation."""

    first_h2 = next((heading for heading in context.headings if heading.level == 2), None)
    has_overview = context.h2("at a glance") is not None
    overview_fields = (
        "product.audience",
        "product.problems_solved",
        "product.capabilities",
        "product.formats",
        "product.compatibility",
    )
    overview_fact_candidates = [
        selected.fact_id
        for field in overview_fields
        if (selected := accepted_fact(context.facts, field)) is not None
    ]
    overview_fact_ids: list[str] = []
    authored_summary_fact_ids: list[str] = []
    operations: list[ReadmeDocumentOperationV1] = []
    overview_insert = ""
    summary: str | None = None
    if agentic_plan is not None and agentic_plan.opening_summary is not None:
        summary = agentic_plan.opening_summary.text.strip()
        authored_summary_fact_ids.extend(agentic_plan.opening_summary.supporting_fact_ids)
    h1 = next((heading for heading in context.headings if heading.level == 1), None)
    if summary and h1 is not None:
        opening_end = first_h2.start if first_h2 is not None else len(context.inner_text)
        badges = list(_BADGE_LINE.finditer(context.inner_text, h1.heading_end, opening_end))
        summary_start = badges[-1].end() if badges else h1.heading_end
        replacement = f"\n{summary}\n\n"
        if context.inner_text[summary_start:opening_end] != replacement:
            operations.append(
                build_operation(
                    operation_id="readme.opening.fact-backed-summary",
                    operation="replace",
                    source=context.source,
                    start=context.byte_offset(summary_start),
                    end=context.byte_offset(opening_end),
                    replacement=replacement,
                    fact_ids=sorted(set(authored_summary_fact_ids)),
                    treatment="authoritative_fact_correction",
                    rationale=(
                        "Replace competing opening calls-to-action and summaries with exactly "
                        "one product-first statement bound to accepted repository facts."
                    ),
                )
            )
    elif summary and product_explanation_offset(context.inner_text) is None:
        overview_insert = summary + "\n\n"
    if not has_overview:
        rendered_overview = overview_text(
            context.facts,
            context.headings,
            (
                [sentence.model_dump(mode="json") for sentence in agentic_plan.overview_sentences]
                if agentic_plan is not None
                else None
            ),
            visual_plan.mermaid_markdown,
            omitted_fields=frozenset({"product.limitations"}),
        )
        overview_insert += rendered_overview + "\n\n"
        if agentic_plan is not None:
            overview_fact_ids.extend(
                fact_id
                for sentence in agentic_plan.overview_sentences
                for fact_id in sentence.supporting_fact_ids
            )
        else:
            overview_fact_ids.extend(
                literal_fact_ids(rendered_overview, context.facts, overview_fact_candidates)
            )
        overview_fact_ids.extend(
            fact_id for node in visual_plan.diagram_nodes for fact_id in node.fact_ids
        )
    if not overview_insert:
        return operations
    char_offset = first_h2.start if first_h2 is not None else len(context.inner_text)
    byte_offset = (
        insertion_byte_offset
        if insertion_byte_offset is not None
        else context.byte_offset(char_offset)
    )
    operations.append(
        build_operation(
            operation_id="readme.overview-navigation-and-acquisition",
            operation="insert_before",
            source=context.source,
            start=byte_offset,
            end=byte_offset,
            replacement=overview_insert,
            fact_ids=sorted(
                {
                    *literal_fact_ids(overview_insert, context.facts, overview_fact_ids),
                    *visual_plan.diagram_fact_ids,
                    *authored_summary_fact_ids,
                }
            ),
            treatment="additive",
            rationale=(
                "Put verified audience, purpose, scope, and navigation before secondary "
                "repository detail."
            ),
        )
    )
    return operations


def build_promotional_callout_operations(
    context: DocumentRenderContext,
) -> list[ReadmeDocumentOperationV1]:
    """Remove a top promotional callout when verified relationship context exists elsewhere."""

    relationship = accepted_fact(context.facts, "relationship.commercial_foss")
    callout = _PROMOTIONAL_CALLOUT.search(context.inner_text)
    if callout is None or relationship is None:
        return []
    return [
        build_operation(
            operation_id="readme.opening.remove-promotional-callout",
            operation="remove",
            source=context.source,
            start=context.byte_offset(callout.start()),
            end=context.byte_offset(callout.end()),
            replacement="",
            fact_ids=[relationship.fact_id],
            treatment="authoritative_fact_correction",
            rationale=(
                "Keep the first screen product-first; the existing relationship section "
                "continues to carry restrained commercial context."
            ),
        )
    ]
