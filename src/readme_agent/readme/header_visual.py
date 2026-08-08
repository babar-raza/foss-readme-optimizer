"""Render and validate fact-backed README badges and Mermaid overview graphs."""

from __future__ import annotations

import re

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.diagram_role_semantics import (
    normalize_diagram_role_nodes,
    selected_verified_capability_nodes,
)
from readme_agent.readme.header_badges import render_readme_badges
from readme_agent.readme.header_visual_mermaid import render_capability_landscape
from readme_agent.readme.header_visual_models import (
    MermaidNodeV1,
    ReadmeHeaderVisualV1,
    safe_mermaid_label,
)
from readme_agent.readme.header_visual_validation import validate_readme_header_visual
from readme_agent.readme.presentation_contract import (
    PRESENTATION_MERMAID_MIN_CAPABILITIES,
    PRESENTATION_MERMAID_MIN_INPUTS,
    PRESENTATION_MERMAID_MIN_OUTPUTS,
    PRESENTATION_MERMAID_TARGET_CAPABILITIES,
    PRESENTATION_MERMAID_TARGET_INPUTS,
    PRESENTATION_MERMAID_TARGET_OUTPUTS,
)
from readme_agent.readme.public_vocabulary import (
    canonical_abbreviations_from_facts,
    canonicalize_abbreviations,
)


def _fallback_nodes(facts: ProductFactsV2) -> list[MermaidNodeV1]:
    """Build the same evidence-classified graph without agentic vocabulary."""

    identity = visitor_fact_render_view(facts, "product.identity")
    if identity is None or not identity.phrases:
        return []
    product_label = safe_mermaid_label(identity.phrases[0])
    if product_label is None:
        return []
    nodes = [
        MermaidNodeV1(
            node_id="PRODUCT",
            role="product",
            label=product_label,
            fact_ids=identity.citation_fact_ids,
        )
    ]
    normalized = normalize_diagram_role_nodes(
        [],
        facts,
        {
            "input": PRESENTATION_MERMAID_MIN_INPUTS,
            "capability": PRESENTATION_MERMAID_MIN_CAPABILITIES,
            "output": PRESENTATION_MERMAID_MIN_OUTPUTS,
        },
    )
    counters = {"input": 0, "capability": 0, "output": 0}
    for proposed in normalized:
        counters[proposed.role] += 1
        label = safe_mermaid_label(proposed.label)
        if label is None:
            raise ValueError("unsafe Mermaid label selected from accepted product facts")
        nodes.append(
            MermaidNodeV1(
                node_id={"input": "I", "capability": "C", "output": "O"}[proposed.role]
                + str(counters[proposed.role]),
                role=proposed.role,
                label=label,
                fact_ids=proposed.supporting_fact_ids,
            )
        )
    return nodes


def _agentic_nodes(
    facts: ProductFactsV2,
    plan: ReadmeAgenticCompositionPlanV1,
) -> list[MermaidNodeV1]:
    identity = visitor_fact_render_view(facts, "product.identity")
    if identity is None or not identity.phrases:
        return []
    product_label = safe_mermaid_label(identity.phrases[0])
    if product_label is None:
        return []
    nodes = [
        MermaidNodeV1(
            node_id="PRODUCT",
            role="product",
            label=product_label,
            fact_ids=identity.citation_fact_ids,
        )
    ]
    normalized = normalize_diagram_role_nodes(
        plan.diagram.nodes,
        facts,
        {
            "input": PRESENTATION_MERMAID_MIN_INPUTS,
            "capability": PRESENTATION_MERMAID_MIN_CAPABILITIES,
            "output": PRESENTATION_MERMAID_MIN_OUTPUTS,
        },
        target_counts={
            "input": PRESENTATION_MERMAID_TARGET_INPUTS,
            "capability": PRESENTATION_MERMAID_TARGET_CAPABILITIES,
            "output": PRESENTATION_MERMAID_TARGET_OUTPUTS,
        },
    )
    counters = {"input": 0, "capability": 0, "output": 0}
    for proposed in normalized:
        counters[proposed.role] += 1
        label = safe_mermaid_label(proposed.label)
        if label is None:
            raise ValueError("unsafe Mermaid label selected by the composition plan")
        nodes.append(
            MermaidNodeV1(
                node_id={"input": "I", "capability": "C", "output": "O"}[proposed.role]
                + str(counters[proposed.role]),
                role=proposed.role,
                label=label,
                fact_ids=proposed.supporting_fact_ids,
            )
        )
    return nodes


def render_readme_header_visual(
    facts: ProductFactsV2,
    agentic_plan: ReadmeAgenticCompositionPlanV1 | None = None,
) -> ReadmeHeaderVisualV1:
    """Render the applicable factual badge row and repository-specific Mermaid graph."""

    identity = visitor_fact_render_view(facts, "product.identity")
    if identity is None or not identity.phrases:
        raise ValueError("README header has no accepted product identity")
    title = " ".join(identity.phrases[0].split()).strip()
    if not title or any(token in title for token in ("<!--", "-->", "#", "<", ">")):
        raise ValueError("README header has an unsafe product identity")
    canonical_terms = canonical_abbreviations_from_facts(facts)
    badges = [
        badge.model_copy(
            update={
                "alt_text": canonicalize_abbreviations(badge.alt_text, canonical_terms),
            }
        )
        for badge in render_readme_badges(facts)
    ]
    nodes = (
        _agentic_nodes(facts, agentic_plan)
        if agentic_plan is not None and agentic_plan.diagram.nodes
        else _fallback_nodes(facts)
    )
    expected_capabilities = selected_verified_capability_nodes(facts)
    rendered_capability_labels = {
        " ".join(node.label.casefold().split()) for node in nodes if node.role == "capability"
    }
    missing_capabilities = [
        node.label
        for node in expected_capabilities
        if " ".join(node.label.casefold().split()) not in rendered_capability_labels
    ]
    if missing_capabilities:
        raise ValueError(
            "README diagram omits selected verified capabilities: "
            + ", ".join(missing_capabilities)
        )
    role_counts = {
        role: sum(node.role == role for node in nodes) for role in ("input", "capability", "output")
    }
    if (
        agentic_plan is not None
        and agentic_plan.diagram.nodes
        and (
            role_counts["input"] < PRESENTATION_MERMAID_MIN_INPUTS
            or role_counts["capability"] < PRESENTATION_MERMAID_MIN_CAPABILITIES
            or role_counts["output"] < PRESENTATION_MERMAID_MIN_OUTPUTS
        )
    ):
        raise ValueError("README diagram lacks accepted input, capability, or output detail")
    if len(nodes) < 2:
        raise ValueError("README diagram has no accepted repository-specific detail")
    badge_markdown = " ".join(
        (
            f"[![{badge.alt_text}]({badge.image_url})]({badge.target_url})"
            if badge.target_url
            else f"![{badge.alt_text}]({badge.image_url})"
        )
        for badge in badges
    )
    mermaid_source = render_capability_landscape(nodes)
    mermaid_markdown = f"```mermaid\n{mermaid_source}\n```"
    visual = ReadmeHeaderVisualV1(
        title=title,
        title_fact_ids=identity.citation_fact_ids,
        badges=badges,
        badge_markdown=badge_markdown,
        diagram_nodes=nodes,
        mermaid_source=mermaid_source,
        mermaid_markdown=mermaid_markdown,
    )
    verdict = validate_readme_header_visual(visual, facts)
    if not verdict.valid:
        raise ValueError("invalid README header visual: " + "; ".join(verdict.errors))
    return visual


def has_marker_free_presentation_contract(text: str) -> bool:
    """Recognize the visible header/diagram seam without hidden README metadata."""

    if "<!--" in text or "readme-agent" in text:
        return False
    return bool(
        re.search(r"(?m)^# .+\n", text)
        and re.search(r"(?m)^(?:!\[|\[!\[)", text)
        and re.search(
            r"(?msi)^## At a Glance\s+.*?^```mermaid\nflowchart LR\n",
            text,
        )
    )
