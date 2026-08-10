"""Render the deterministic hub-and-spoke Mermaid capability landscape."""

from __future__ import annotations

import re
import textwrap

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.header_visual_layout import render_capability_group
from readme_agent.readme.header_visual_models import MermaidNodeV1
from readme_agent.readme.presentation_contract import (
    PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS,
)

_WIDE_ENDPOINT_GROUP_MINIMUM = 4
_RASTER_ENCODER_EXPORTS = frozenset({"encode_png", "encode_jpeg"})
_RASTER_FORMATS_LABEL = "PNG/JPEG"
_CONVERSION_LABEL = re.compile(r"(?i)^(?P<inputs>.+?) to (?P<outputs>.+?) conversion$")
_IMAGE_ENDPOINT = re.compile(r"(?i)^images?$")
_IMAGE_FILES_LABEL = re.compile(r"(?i)^images? files$")
_ENDPOINT_DIRECTION_WORD = re.compile(r"(?i)\b(?:input|output)\b")
_FILES_SUFFIX = re.compile(r"(?i)\s+files$")
_ENDPOINT_LINE_WIDTH = 20


def endpoint_mermaid_label(label: str) -> str:
    """Wrap and pad one endpoint label to a common GitHub-Mermaid box width."""

    lines = textwrap.wrap(
        " ".join(label.split()),
        width=_ENDPOINT_LINE_WIDTH,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [label]
    return "<br/>".join(line + "&nbsp;" * (_ENDPOINT_LINE_WIDTH - len(line)) for line in lines)


def raster_output_formats_label(facts: ProductFactsV2) -> str | None:
    """Name the concrete raster formats only when their encoders are public API."""

    try:
        api = facts.selected_fact("api.public_surface")
    except (KeyError, ValueError):
        return None
    if api.verification_state not in {"verified", "policy_approved"} or (
        api.has_unresolved_conflict
    ):
        return None
    if not isinstance(api.value, dict):
        return None
    catalog = api.value.get("coordinate_catalog")
    module_lists = [
        api.value.get("modules"),
        catalog.get("modules") if isinstance(catalog, dict) else None,
    ]
    exports = {
        str(export).casefold()
        for modules in module_lists
        if isinstance(modules, list)
        for module in modules
        if isinstance(module, dict)
        for export in module.get("exports", [])
        if isinstance(export, str)
    }
    if _RASTER_ENCODER_EXPORTS <= exports:
        return _RASTER_FORMATS_LABEL
    return None


def compact_diagram_node_label(
    label: str,
    role: str,
    *,
    raster_output_formats: str | None = None,
    product_name: str | None = None,
) -> str:
    """Shorten one node label by deterministic rules without deleting information."""

    text = " ".join(label.split())
    if role == "product":
        return text
    if role == "capability":
        conversion = _CONVERSION_LABEL.fullmatch(text)
        if conversion is not None:
            outputs = conversion.group("outputs")
            if raster_output_formats and _IMAGE_ENDPOINT.fullmatch(outputs):
                outputs = raster_output_formats
            text = f"{conversion.group('inputs')} to {outputs}"
    else:
        text = " ".join(_ENDPOINT_DIRECTION_WORD.sub("", text).split())
        if raster_output_formats:
            text = _IMAGE_FILES_LABEL.sub(f"{raster_output_formats} images", text)
    if len(text) > PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS:
        shortened = _FILES_SUFFIX.sub("", text)
        if product_name and len(shortened) > PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS:
            without_product = " ".join(
                re.sub(re.escape(product_name), "", shortened, flags=re.IGNORECASE).split()
            ).strip(" -:,")
            if without_product:
                shortened = without_product
        if len(shortened) <= PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS:
            text = shortened
        else:
            words = textwrap.shorten(
                shortened,
                width=PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS,
                placeholder="",
            ).rstrip(" ,;:-")
            words = re.sub(r"(?i)\s+(?:and|or|to|for|with)$", "", words).rstrip(" ,;:-")
            text = words or shortened[:PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS].rstrip()
    return text


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
        if len(grouped["input"]) >= _WIDE_ENDPOINT_GROUP_MINIMUM:
            lines.append("    direction LR")
        lines.extend(
            f'    {node.node_id}["{endpoint_mermaid_label(node.label)}"]'
            for node in grouped["input"]
        )
        lines.append("  end")
    lines.append(f'  {product.node_id}["{product.label}"]')
    lines.extend(render_capability_group(grouped["capability"]))
    if grouped["output"]:
        lines.append('  subgraph Outputs["Outputs"]')
        if len(grouped["output"]) >= _WIDE_ENDPOINT_GROUP_MINIMUM:
            lines.append("    direction LR")
        lines.extend(
            f'    {node.node_id}["{endpoint_mermaid_label(node.label)}"]'
            for node in grouped["output"]
        )
        lines.append("  end")
    lines.extend(f"  {node.node_id} --- {product.node_id}" for node in grouped["input"])
    lines.append(f"  {product.node_id} --- Capabilities")
    if grouped["output"]:
        lines.append("  Capabilities --- Outputs")
    return "\n".join(lines)
