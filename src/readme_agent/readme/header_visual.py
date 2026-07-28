"""Render and validate fact-backed README badges and Mermaid overview graphs."""

from __future__ import annotations

import re
from typing import Literal

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.header_badges import render_readme_badges
from readme_agent.readme.header_visual_models import (
    MermaidNodeV1,
    ReadmeHeaderVisualV1,
    safe_mermaid_label,
)
from readme_agent.readme.header_visual_validation import validate_readme_header_visual


def _render_nodes(facts: ProductFactsV2) -> list[MermaidNodeV1]:
    nodes: list[MermaidNodeV1] = []
    identity = visitor_fact_render_view(facts, "product.identity")
    if identity is None or not identity.phrases:
        return []
    product_label = safe_mermaid_label(identity.phrases[0])
    if product_label is None:
        return []
    nodes.append(
        MermaidNodeV1(
            node_id="product",
            role="product",
            label=product_label,
            fact_ids=identity.citation_fact_ids,
        )
    )
    limits = {
        "product.audience": 1,
        "product.problems_solved": 1,
        "product.capabilities": 2,
        "product.formats": 2,
    }
    roles: dict[
        str,
        Literal["audience", "problem", "capability", "format"],
    ] = {
        "product.audience": "audience",
        "product.problems_solved": "problem",
        "product.capabilities": "capability",
        "product.formats": "format",
    }
    for field, maximum in limits.items():
        view = visitor_fact_render_view(facts, field)
        if view is None:
            continue
        role = roles[field]
        accepted_labels = [safe_mermaid_label(phrase) for phrase in view.phrases[:maximum]]
        if any(label is None for label in accepted_labels):
            raise ValueError(f"unsafe Mermaid label selected from accepted {field} fact")
        for index, label in enumerate(accepted_labels, start=1):
            assert label is not None
            nodes.append(
                MermaidNodeV1(
                    node_id=f"{role}_{index}",
                    role=role,
                    label=label,
                    fact_ids=view.citation_fact_ids,
                )
            )
    return nodes


def render_readme_header_visual(facts: ProductFactsV2) -> ReadmeHeaderVisualV1:
    """Render the applicable factual badge row and repository-specific Mermaid graph."""

    identity = visitor_fact_render_view(facts, "product.identity")
    if identity is None or not identity.phrases:
        raise ValueError("README header has no accepted product identity")
    title = " ".join(identity.phrases[0].split()).strip()
    if not title or any(token in title for token in ("<!--", "-->", "#", "<", ">")):
        raise ValueError("README header has an unsafe product identity")
    badges = render_readme_badges(facts)
    nodes = _render_nodes(facts)
    if len(nodes) < 2:
        raise ValueError("README diagram has no accepted repository-specific branch")
    badge_markdown = " ".join(
        (
            f"[![{badge.alt_text}]({badge.image_url})]({badge.target_url})"
            if badge.target_url
            else f"![{badge.alt_text}]({badge.image_url})"
        )
        for badge in badges
    )
    mermaid_lines = ["flowchart LR"]
    mermaid_lines.extend(f'  {node.node_id}["{node.label}"]' for node in nodes)
    mermaid_lines.extend(
        f"  product --> {node.node_id}" for node in nodes if node.node_id != "product"
    )
    mermaid_source = "\n".join(mermaid_lines)
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
