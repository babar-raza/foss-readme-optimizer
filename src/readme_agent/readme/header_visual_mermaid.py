"""Render the deterministic corporate Mermaid capability landscape."""

from __future__ import annotations

import re
import textwrap

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.header_visual_layout import render_capability_group
from readme_agent.readme.header_visual_models import MermaidNodeV1
from readme_agent.readme.presentation_contract import PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS

_RASTER_ENCODER_EXPORTS = frozenset({"encode_png", "encode_jpeg"})
_RASTER_FORMATS_LABEL = "PNG/JPEG"
_CONVERSION_LABEL = re.compile(r"(?i)^(?P<inputs>.+?) to (?P<outputs>.+?) conversion$")
_IMAGE_ENDPOINT = re.compile(r"(?i)^images?$")
_IMAGE_FILES_LABEL = re.compile(r"(?i)^images? files$")
_ENDPOINT_DIRECTION_WORD = re.compile(r"(?i)\b(?:input|output)\b")
_FILES_SUFFIX = re.compile(r"(?i)\s+files$")
_PAREN_EXTENSION = re.compile(r"\(\.(?P<extension>[A-Za-z0-9]+)\)")
_ENDPOINT_LINE_WIDTH = 20
_CAPABILITY_LINE_WIDTH = 22


def _wrapped_label(label: str, width: int) -> str:
    lines = textwrap.wrap(
        " ".join(label.split()),
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [label]
    return "<br/>".join(lines)


def endpoint_mermaid_label(label: str) -> str:
    """Render concise, consistently sized format endpoints."""

    text = _FILES_SUFFIX.sub("", " ".join(label.split()))
    text = _PAREN_EXTENSION.sub(lambda match: f".{match.group('extension').upper()}", text)
    return _wrapped_label(text, _ENDPOINT_LINE_WIDTH)


def capability_mermaid_label(label: str) -> str:
    """Wrap a capability without changing its fact-backed wording."""

    return _wrapped_label(label, _CAPABILITY_LINE_WIDTH)


def product_mermaid_label(label: str) -> str:
    """Keep the full product name while balancing the central product box."""

    if " FOSS for " in label:
        return label.replace(" FOSS for ", " FOSS<br/>for ", 1)
    return _wrapped_label(label, 24)


def raster_output_formats_label(facts: ProductFactsV2) -> str | None:
    """Name the concrete raster formats only when their encoders are public API."""

    try:
        api = facts.selected_fact("api.public_surface")
    except (KeyError, ValueError):
        return None
    if api.verification_state not in {"verified", "policy_approved"} or api.has_unresolved_conflict:
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
    return _RASTER_FORMATS_LABEL if _RASTER_ENCODER_EXPORTS <= exports else None


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
    """Render a clear input-to-product-to-capabilities-to-output relationship."""

    product = nodes[0]
    grouped = {
        role: [node for node in nodes if node.role == role]
        for role in ("input", "capability", "output")
    }
    display_labels = {
        node.node_id: (
            endpoint_mermaid_label(node.label)
            if node.role in {"input", "output"}
            else capability_mermaid_label(node.label)
        )
        for node in grouped["input"] + grouped["capability"] + grouped["output"]
    }
    lines = ["flowchart LR"]
    if grouped["input"]:
        lines.extend(('  subgraph INPUTS["Inputs & Formats"]', "    direction TB"))
        lines.extend(
            f'    {node.node_id}["{display_labels[node.node_id]}"]' for node in grouped["input"]
        )
        lines.append("  end")
    lines.append(f'  {product.node_id}["{product_mermaid_label(product.label)}"]')
    lines.extend(render_capability_group(grouped["capability"], display_labels))
    if grouped["output"]:
        lines.extend(('  subgraph OUTPUTS["Outputs"]', "    direction TB"))
        lines.extend(
            f'    {node.node_id}["{display_labels[node.node_id]}"]' for node in grouped["output"]
        )
        lines.append("  end")
    if grouped["input"]:
        lines.append(f"  {grouped['input'][0].node_id} --> {product.node_id}")
    lines.append(f"  {product.node_id} --> CORE")
    if grouped["output"]:
        lines.append(f"  CORE --> {grouped['output'][0].node_id}")
    lines.extend(
        (
            (
                "  classDef product fill:#1F4E79,color:#FFFFFF,stroke:#163A5B,"
                "stroke-width:2px,font-weight:bold;"
            ),
            "  classDef input fill:#EAF2F8,color:#17324D,stroke:#7EA6C4,stroke-width:1.5px;",
            "  classDef capability fill:#F7F9FC,color:#243447,stroke:#AAB7C4,stroke-width:1.25px;",
            (
                "  classDef output fill:#EAF6EF,color:#244A32,stroke:#78A889,"
                "stroke-width:1.5px,font-weight:bold;"
            ),
            f"  class {product.node_id} product;",
        )
    )
    if grouped["input"]:
        lines.append(f"  class {','.join(node.node_id for node in grouped['input'])} input;")
    lines.append(f"  class {','.join(node.node_id for node in grouped['capability'])} capability;")
    if grouped["output"]:
        lines.append(f"  class {','.join(node.node_id for node in grouped['output'])} output;")
    if grouped["input"]:
        lines.append("  style INPUTS fill:#F8FBFD,stroke:#7EA6C4,stroke-width:1.5px")
    lines.append("  style CORE fill:#FFFFFF,stroke:#5F7791,stroke-width:2px")
    if len(grouped["capability"]) > 5:
        lines.extend(
            (
                "  style CORE_LEFT fill:transparent,stroke:transparent",
                "  style CORE_RIGHT fill:transparent,stroke:transparent",
            )
        )
    if grouped["output"]:
        lines.append("  style OUTPUTS fill:#F7FBF8,stroke:#78A889,stroke-width:1.5px")
    lines.append("  linkStyle default stroke:#526D82,stroke-width:2px")
    return "\n".join(lines)
