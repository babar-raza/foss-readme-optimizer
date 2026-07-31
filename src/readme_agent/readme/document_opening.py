"""Plan product-first README opening and overview operations."""

from __future__ import annotations

import re

from readme_agent.facts.render_views import visitor_fact_render_view
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


def _fallback_opening_summary(context: DocumentRenderContext) -> tuple[str, list[str]] | None:
    identity = visitor_fact_render_view(context.facts, "product.identity")
    purpose = visitor_fact_render_view(context.facts, "product.capabilities")
    if identity is None or not identity.phrases or purpose is None or not purpose.phrases:
        return None
    identity_fact = context.facts.fact_by_id(identity.fact_id)
    identity_value = identity_fact.value if isinstance(identity_fact.value, dict) else {}
    platform = str(identity_value.get("platform") or identity_value.get("ecosystem") or "").strip()
    kind = f"{platform} library" if platform else "library"
    summary = (
        f"{identity.phrases[0]} is a {kind} that provides "
        f"{purpose.phrases[0].strip().rstrip('.').lower()}."
    )
    return summary, [identity.fact_id, purpose.fact_id]


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
    overview_insert = ""
    if (
        agentic_plan is not None
        and agentic_plan.opening_summary is not None
        and product_explanation_offset(context.inner_text) is None
        and agentic_plan.opening_summary.text.strip() not in context.inner_text
    ):
        overview_insert = agentic_plan.opening_summary.text.strip() + "\n\n"
        authored_summary_fact_ids.extend(agentic_plan.opening_summary.supporting_fact_ids)
    elif product_explanation_offset(context.inner_text) is None:
        fallback_summary = _fallback_opening_summary(context)
        if fallback_summary is not None:
            summary, fact_ids = fallback_summary
            if summary not in context.inner_text:
                overview_insert = summary + "\n\n"
                authored_summary_fact_ids.extend(fact_ids)
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
        return []
    char_offset = first_h2.start if first_h2 is not None else len(context.inner_text)
    byte_offset = (
        insertion_byte_offset
        if insertion_byte_offset is not None
        else context.byte_offset(char_offset)
    )
    return [
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
    ]


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
