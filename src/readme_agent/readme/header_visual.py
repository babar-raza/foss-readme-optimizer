"""Render and validate fact-backed README badges and Mermaid overview graphs."""

from __future__ import annotations

import re
from typing import Literal

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.header_badges import render_readme_badges
from readme_agent.readme.header_visual_models import (
    MermaidNodeV1,
    ReadmeHeaderVisualV1,
    safe_mermaid_label,
)
from readme_agent.readme.header_visual_validation import validate_readme_header_visual


def _fallback_nodes(facts: ProductFactsV2) -> list[MermaidNodeV1]:
    """Build a conservative diagram when compatibility callers supply no agentic vocabulary."""

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
    limits: dict[str, tuple[Literal["input", "capability", "output"], int]] = {
        "product.formats": ("input", 3),
        "product.capabilities": ("capability", 6),
        "product.problems_solved": ("output", 1),
    }
    for field, (role, maximum) in limits.items():
        view = visitor_fact_render_view(facts, field)
        if view is None:
            continue
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
    capabilities = [node for node in nodes if node.role == "capability"]
    if len(capabilities) < 3:
        problem = visitor_fact_render_view(facts, "product.problems_solved")
        if problem is not None:
            for phrase in problem.phrases:
                if len(capabilities) >= 3:
                    break
                label = safe_mermaid_label(phrase)
                if label is None or any(node.label == label for node in capabilities):
                    continue
                node = MermaidNodeV1(
                    node_id=f"capability_{len(capabilities) + 1}",
                    role="capability",
                    label=label,
                    fact_ids=problem.citation_fact_ids,
                )
                nodes.append(node)
                capabilities.append(node)
    if not any(node.role == "output" for node in nodes) and capabilities:
        source = capabilities[-1]
        nodes.append(
            MermaidNodeV1(
                node_id="output_1",
                role="output",
                label=source.label,
                fact_ids=source.fact_ids,
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
            node_id="product",
            role="product",
            label=product_label,
            fact_ids=identity.citation_fact_ids,
        )
    ]
    counters = {"input": 0, "capability": 0, "output": 0}
    for proposed in plan.diagram.nodes:
        counters[proposed.role] += 1
        label = safe_mermaid_label(proposed.label)
        if label is None:
            raise ValueError("unsafe Mermaid label selected by the composition plan")
        nodes.append(
            MermaidNodeV1(
                node_id=f"{proposed.role}_{counters[proposed.role]}",
                role=proposed.role,
                label=label,
                fact_ids=proposed.supporting_fact_ids,
            )
        )
    return nodes


def _mermaid_source(nodes: list[MermaidNodeV1]) -> str:
    product = nodes[0]
    grouped = {
        role: [node for node in nodes if node.role == role]
        for role in ("input", "capability", "output")
    }
    lines = ["flowchart LR", '  subgraph Inputs["Inputs and formats"]']
    lines.extend(f'    {node.node_id}["{node.label}"]' for node in grouped["input"])
    lines.extend(["  end", "", f'  {product.node_id}["{product.label}"]', ""])
    lines.append('  subgraph Capabilities["Core capabilities"]')
    lines.extend(f'    {node.node_id}["{node.label}"]' for node in grouped["capability"])
    lines.extend(["  end", "", '  subgraph Outputs["Outputs and accessible content"]'])
    lines.extend(f'    {node.node_id}["{node.label}"]' for node in grouped["output"])
    lines.extend(["  end", ""])
    lines.extend(f"  {node.node_id} --- product" for node in grouped["input"])
    lines.extend(f"  product --- {node.node_id}" for node in grouped["capability"])
    outputs = grouped["output"]
    for index, node in enumerate(grouped["capability"]):
        if outputs:
            lines.append(f"  {node.node_id} --- {outputs[index % len(outputs)].node_id}")
    return "\n".join(lines)


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
    badges = render_readme_badges(facts)
    nodes = (
        _agentic_nodes(facts, agentic_plan)
        if agentic_plan is not None and agentic_plan.diagram.nodes
        else _fallback_nodes(facts)
    )
    role_counts = {
        role: sum(node.role == role for node in nodes) for role in ("input", "capability", "output")
    }
    if (
        agentic_plan is not None
        and agentic_plan.diagram.nodes
        and (role_counts["input"] < 1 or role_counts["capability"] < 3 or role_counts["output"] < 1)
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
    mermaid_source = _mermaid_source(nodes)
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
