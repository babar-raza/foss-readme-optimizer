"""Plan product-first README opening and overview operations."""

from __future__ import annotations

import re

from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_templates import (
    accepted_fact,
    example_text,
    installation_text,
    overview_text,
)
from readme_agent.readme.fact_grounding import literal_fact_ids
from readme_agent.readme.header_visual_models import ReadmeHeaderVisualV1

_PROMOTIONAL_CALLOUT = re.compile(
    r"(?m)^>[^\n]*(?:products\.aspose\.org)[^\n]*(?:products\.aspose\.com)[^\n]*\n(?:\n)?",
    re.IGNORECASE,
)


def build_opening_operations(
    context: DocumentRenderContext,
    agentic_plan: ReadmeAgenticCompositionPlanV1 | None,
    visual_plan: ReadmeHeaderVisualV1,
) -> list[ReadmeDocumentOperationV1]:
    """Add missing overview, acquisition, and minimal-example sections as one operation."""

    first_h2 = next((heading for heading in context.headings if heading.level == 2), None)
    has_overview = context.h2("at a glance") is not None
    installation = context.h2("installation")
    overview_fields = (
        "product.audience",
        "product.problems_solved",
        "product.capabilities",
        "product.formats",
        "product.compatibility",
        "product.limitations",
    )
    overview_fact_candidates = [
        selected.fact_id
        for field in overview_fields
        if (selected := accepted_fact(context.facts, field)) is not None
    ]
    overview_fact_ids: list[str] = []
    derived_installation_fact_ids: list[str] = []
    verified_installation = installation_text(
        context.facts,
        context.org_repo,
        context.base_revision,
    )
    overview_insert = ""
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
        )
        overview_insert = rendered_overview + "\n\n"
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
    if installation is None and verified_installation:
        overview_insert += "## Installation\n\n" + verified_installation + "\n\n"
        derived_installation_fact_ids.extend(
            selected.fact_id
            for field in ("installation.coordinates", "installation.verified_acquisition")
            if (selected := accepted_fact(context.facts, field)) is not None
        )
    example = accepted_fact(context.facts, "example.minimal")
    example_value = example.value if example is not None and isinstance(example.value, dict) else {}
    exact_code = str(example_value.get("code", "")).rstrip()
    example_target = context.h2("quick start", "usage")
    if exact_code and exact_code not in context.inner_text and example_target is None:
        overview_insert += (
            "## Quick Start\n\n" + example_text(context.facts, context.base_revision) + "\n\n"
        )
        assert example is not None
        overview_fact_ids.append(example.fact_id)
    if not overview_insert:
        return []
    char_offset = first_h2.start if first_h2 is not None else len(context.inner_text)
    byte_offset = context.byte_offset(char_offset)
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
                    *derived_installation_fact_ids,
                }
            ),
            treatment="additive",
            rationale=(
                "Put verified audience, purpose, scope, navigation, and any missing source "
                "acquisition path before secondary repository detail."
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
