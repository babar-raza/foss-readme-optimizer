"""Render the deterministic hub-and-spoke Mermaid capability landscape."""

from __future__ import annotations

from readme_agent.readme.header_visual_layout import render_capability_group
from readme_agent.readme.header_visual_models import MermaidNodeV1


def render_capability_landscape(nodes: list[MermaidNodeV1]) -> str:
    """Render evidence-classified nodes without inferring new roles or relationships."""

    product = nodes[0]
    grouped = {
        role: [node for node in nodes if node.role == role]
        for role in ("input", "capability", "output")
    }
    lines = ["flowchart LR"]
    if grouped["input"]:
        lines.append('  subgraph Inputs["Inputs and Formats"]')
        lines.extend(f'    {node.node_id}["{node.label}"]' for node in grouped["input"])
        lines.extend(("  end", ""))
    lines.extend((f'  {product.node_id}["{product.label}"]', ""))
    lines.extend((*render_capability_group(grouped["capability"]), ""))
    if grouped["output"]:
        lines.append('  subgraph Outputs["Outputs"]')
        lines.extend(f'    {node.node_id}["{node.label}"]' for node in grouped["output"])
        lines.extend(("  end", ""))
    lines.extend(f"  {node.node_id} --- {product.node_id}" for node in grouped["input"])
    lines.append(f"  {product.node_id} --- Capabilities")
    if grouped["output"]:
        lines.append("  Capabilities --- Outputs")
    return "\n".join(lines)
