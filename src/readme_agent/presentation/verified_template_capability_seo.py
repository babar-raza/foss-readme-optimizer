"""Create search-intent capability titles from accepted product facts."""

from __future__ import annotations

import re
from dataclasses import dataclass

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.capability_semantics import is_action_led_capability_title
from readme_agent.readme.diagram_semantic_candidates import (
    input_node_candidates,
    output_node_candidates,
)
from readme_agent.readme.presentation_similarity import capability_discriminators


@dataclass(frozen=True)
class CapabilitySeoContextV1:
    product_name: str
    platform: str
    primary_input: str
    primary_output: str


def _identity_value(facts: ProductFactsV2, key: str) -> str:
    try:
        value = facts.selected_fact("product.identity").value
    except KeyError:
        return ""
    return str(value.get(key) or "").strip() if isinstance(value, dict) else ""


def capability_seo_context(facts: ProductFactsV2) -> CapabilitySeoContextV1:
    """Return accepted product, platform, and directional-format vocabulary."""

    inputs = input_node_candidates(facts)
    outputs = output_node_candidates(facts)
    return CapabilitySeoContextV1(
        product_name=_identity_value(facts, "product_name"),
        platform=_identity_value(facts, "platform").title(),
        primary_input=inputs[0].label if inputs else "",
        primary_output=outputs[0].label if outputs else "",
    )


def _destination(value: str) -> str:
    return re.sub(r"(?i)\s+files$", "", value).strip()


def _short_subject(value: str) -> str:
    shortened = re.sub(r"\s*\([^)]*\)", "", value).strip()
    shortened = re.sub(r"(?i)^Microsoft\s+", "", shortened)
    return re.sub(r"(?i)\s+(?:files|documents|content)$", "", shortened).strip()


def seo_capability_title(capability: str, context: CapabilitySeoContextV1) -> str:
    """Turn one verified capability into an action-led, fact-bounded search phrase."""

    title = " ".join(capability.strip().rstrip(".").split())
    lowered = title.casefold()
    subject = context.primary_input
    short_subject = _short_subject(subject)
    output = _destination(context.primary_output)
    short_subject = _short_subject(subject)
    document_label = f"{short_subject} documents" if short_subject else "documents"
    format_exchange = re.fullmatch(r"(?i)file\s+format\s+import\s+and\s+export\s+for\s+(.+)", title)
    if format_exchange is not None:
        return f"Import and export {format_exchange.group(1)} files"
    action_directional = re.fullmatch(
        r"(?i)convert\s+(.+?)\s+to\s+(.+?)(?:\s+in\s+[A-Za-z0-9.+#-]+)?$",
        title,
    )
    if action_directional is not None:
        source_format = action_directional.group(1).strip()
        output_format = action_directional.group(2).strip()
        source_label = (
            source_format
            if re.search(r"(?i)\b(?:files|documents|content)$", source_format)
            else f"{source_format} files"
        )
        platform_suffix = f" in {context.platform}" if context.platform else ""
        return f"Convert {source_label} to {output_format}{platform_suffix}"
    directional_conversion = re.fullmatch(r"(?i)(.+?)\s+to\s+(.+?)\s+conversion", title)
    if directional_conversion is not None:
        source_format = directional_conversion.group(1).strip()
        output_format = directional_conversion.group(2).strip()
        source_label = (
            source_format
            if re.search(r"(?i)\b(?:files|documents|content)$", source_format)
            else f"{source_format} files"
        )
        output_label = "images" if output_format.casefold() == "image" else output_format
        platform_suffix = f" in {context.platform}" if context.platform else ""
        return f"Convert {source_label} to {output_label}{platform_suffix}"
    metadata_extraction = re.fullmatch(r"(?i)(.+?\s+metadata)\s+extraction", title)
    if metadata_extraction is not None:
        return f"Extract {metadata_extraction.group(1)}"
    if re.fullmatch(r"(?i)mcp\s+server\s+hosting", title):
        return "Host MCP servers"
    if (
        re.search(r"(?i)\bworkbooks?\b", title)
        and sum(verb in lowered for verb in ("create", "load", "modify", "save")) >= 2
    ):
        return f"Create and manage {subject or 'spreadsheet workbooks'}"
    if "cell" in lowered and "value" in lowered and "style" in lowered:
        return "Edit spreadsheet cell values and styles"
    if "document lifecycle" in lowered or (
        "document" in lowered
        and sum(verb in lowered for verb in ("create", "load", "save", "merge", "inspect")) >= 2
    ):
        return f"Create and manage {document_label}"
    if "editing operations" in lowered:
        return f"Edit {short_subject + ' files' if short_subject else 'files'}"
    if "edit" in lowered and "text" in lowered and "image" in lowered:
        return f"Edit text and images in {document_label}"
    if "resource" in lowered and "limit" in lowered:
        return f"Configure {short_subject + ' ' if short_subject else ''}resource limits"
    if (
        "pdf/a" in lowered
        and "pdf/ua" in lowered
        and any(term in lowered for term in ("check", "conversion", "convert", "validat"))
    ):
        has_validation = any(term in lowered for term in ("check", "validat"))
        has_conversion = any(term in lowered for term in ("conversion", "convert"))
        if has_validation and has_conversion:
            return "Validate and convert PDF/A and PDF/UA documents"
        if has_conversion:
            return "Convert PDF/A and PDF/UA documents"
        return "Validate PDF/A and PDF/UA documents"
    if "signature" in lowered:
        return f"Work with {short_subject + ' ' if short_subject else ''}digital signatures"
    if "xmp" in lowered and "metadata" in lowered:
        if re.search(r"\blow[- ]level\b", lowered) and "object" in lowered:
            return "Work with XMP metadata and low-level PDF objects"
        return "Work with XMP metadata"
    if "primitive" in lowered:
        return f"Create {title}"
    if "animation" in lowered and "keyframe" in lowered:
        return "Create 3D animations with keyframes"
    if re.fullmatch(r"(?i).+\s+export", title):
        return f"Export {_destination(title[:-6].strip())} files"
    if is_action_led_capability_title(title) and capability_discriminators(title):
        # An explicit verified format capability already carries its own
        # direction and subject. Replacing those with the repository-wide
        # primary input/output can turn, for example, DOCX read/write into the
        # different claim DOC-to-DOCX conversion and breaks exact provenance.
        return title
    if subject:
        if "travers" in lowered:
            suffix = f" in {context.platform}" if context.platform else ""
            return f"Read and traverse {subject}{suffix}"
        if "page" in lowered and "title" in lowered:
            return f"Access {short_subject} pages and page titles"
        if "richtext" in lowered or "rich text" in lowered or "formatting" in lowered:
            return f"Extract rich text and formatting from {short_subject} files"
        if "image" in lowered and "attach" in lowered:
            return f"Extract images and attached files from {short_subject} files"
        if "table" in lowered or ("row" in lowered and "cell" in lowered):
            return f"Read {short_subject} tables, rows, and cells"
        if "tag" in lowered:
            return f"Inspect tags in {short_subject} documents"
        if "list" in lowered or "outline" in lowered:
            return f"Read numbered lists and outline elements in {short_subject} documents"
        same_format = bool(
            output and _short_subject(subject).casefold() == _short_subject(output).casefold()
        )
        if same_format and "import" in lowered and "export" in lowered:
            return f"Import and export {subject}"
        if same_format and any(term in lowered for term in ("export", "save", "write")):
            return f"Export {subject}"
        if same_format and any(term in lowered for term in ("import", "load", "read")):
            return f"Import {subject}"
        if any(term in lowered for term in ("export", "convert", "save", "write")) and output:
            return f"Convert {short_subject} files to {output}"
    if is_action_led_capability_title(title):
        return title
    return f"Work with {title}"


__all__ = ["CapabilitySeoContextV1", "capability_seo_context", "seo_capability_title"]
