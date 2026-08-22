"""Resolve explicit document-format roles from accepted product facts."""

from __future__ import annotations

import re
from typing import Literal

from readme_agent.facts.format_vocabulary import (
    DOCUMENT_FORMAT_ABBREVIATIONS,
    canonical_document_format,
)
from readme_agent.facts.schema_v2 import ProductFactsV2

FormatRole = Literal["input", "output"]

_STRUCTURED_ROLE = re.compile(
    r"(?i)^(?P<operation>load|read|import|save|write|export|supported|support|input|output)"
    r"\s+formats?\s*:\s*(?P<formats>.+)$"
)
_BIDIRECTIONAL = re.compile(r"(?i)^(?:load and save|read and write)\s+(?P<formats>.+)$")
_INPUT_OPERATIONS = frozenset({"load", "read", "import", "input"})
_OUTPUT_OPERATIONS = frozenset({"save", "write", "export", "output"})
_DIRECTIONAL_API_SUFFIX = re.compile(
    r"(?i)(?:loadoptions?|saveoptions?|importer|exporter|formatdetector|format|plugin)$"
)
_INPUT_SEMANTICS = re.compile(
    r"(?i)\b(?:load|open|read)s?(?:ed|ing)?\b|(?:Importer|LoadOptions?)\b|"
    r"\.(?:open|load|read)\s*\("
)
_OUTPUT_SEMANTICS = re.compile(
    r"(?i)\b(?:export|save|write)s?(?:ed|ing)?\b|(?:Exporter|SaveOptions?)\b|"
    r"\.(?:save|write)\s*\("
)


def _format_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.split(r"[,;/]|\s+and\s+", value, flags=re.IGNORECASE):
        candidate = re.sub(r"(?i)\b(?:format|formats|file|files)\b", "", raw).strip(" .()")
        canonical = canonical_document_format(candidate)
        if canonical is not None:
            tokens.add(canonical)
    return tokens


def explicit_format_roles(facts: ProductFactsV2 | None) -> dict[str, frozenset[FormatRole]]:
    """Return role authority only for formats explicitly named by ``product.formats``."""

    if facts is None:
        return {}
    fact_id = facts.selected_fact_ids.get("product.formats")
    if fact_id is None:
        return {}
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return {}
    if fact.has_unresolved_conflict or not isinstance(fact.value, list):
        return {}
    roles: dict[str, set[FormatRole]] = {}
    for item in fact.value:
        if not isinstance(item, str):
            continue
        normalized = " ".join(item.split()).strip().rstrip(".")
        structured = _STRUCTURED_ROLE.fullmatch(normalized)
        if structured is not None:
            operation = structured.group("operation").casefold()
            item_roles: set[FormatRole]
            if operation in _INPUT_OPERATIONS:
                item_roles = {"input"}
            elif operation in _OUTPUT_OPERATIONS:
                item_roles = {"output"}
            else:
                item_roles = {"input", "output"}
            formats = _format_tokens(structured.group("formats"))
        elif (bidirectional := _BIDIRECTIONAL.fullmatch(normalized)) is not None:
            item_roles = {"input", "output"}
            formats = _format_tokens(bidirectional.group("formats"))
        else:
            continue
        for format_name in formats:
            roles.setdefault(format_name, set()).update(item_roles)
    return {name: frozenset(values) for name, values in roles.items()}


def mentioned_explicit_formats(text: str, roles: dict[str, frozenset[FormatRole]]) -> set[str]:
    """Return explicitly governed formats mentioned in one visitor-facing fragment."""

    uppercase = text.upper()
    return {
        format_name
        for format_name in roles
        if format_name in DOCUMENT_FORMAT_ABBREVIATIONS
        and re.search(
            rf"(?<![A-Z0-9_-]){re.escape(format_name)}(?![A-Z0-9_-])",
            uppercase,
        )
    }


def mentioned_document_formats(text: str) -> set[str]:
    """Return governed format abbreviations present as standalone public terms."""

    uppercase = text.upper()
    return {
        format_name
        for format_name in DOCUMENT_FORMAT_ABBREVIATIONS
        if re.search(
            rf"(?<![A-Z0-9_-]){re.escape(format_name)}(?![A-Z0-9_-])",
            uppercase,
        )
    }


def formats_in_api_symbol(name: str) -> set[str]:
    """Return governed formats encoded in a compact public API type name."""

    symbol = name.rsplit(".", 1)[-1].split("(", 1)[0].strip("` ")
    stem = _DIRECTIONAL_API_SUFFIX.sub("", symbol)
    canonical = canonical_document_format(stem)
    return {canonical} if canonical is not None else set()


def unsupported_directional_formats(
    text: str,
    facts: ProductFactsV2 | None,
) -> dict[FormatRole, frozenset[str]]:
    """Return unsupported input/output claims made by one public fragment."""

    formats = mentioned_document_formats(text)
    claims: dict[FormatRole, frozenset[str]] = {}
    if _INPUT_SEMANTICS.search(text):
        claims["input"] = frozenset(
            unsupported_format_directions_for_formats(formats, facts, "input")
        )
    if _OUTPUT_SEMANTICS.search(text):
        claims["output"] = frozenset(
            unsupported_format_directions_for_formats(formats, facts, "output")
        )
    return {role: values for role, values in claims.items() if values}


def conflicting_explicit_formats(
    text: str,
    facts: ProductFactsV2 | None,
    role: FormatRole,
) -> set[str]:
    """Return formats whose explicit accepted role excludes the requested role."""

    roles = explicit_format_roles(facts)
    return {
        format_name
        for format_name in mentioned_explicit_formats(text, roles)
        if role not in roles[format_name]
    }


def unsupported_format_directions(
    text: str,
    facts: ProductFactsV2 | None,
    role: FormatRole,
) -> set[str]:
    """Return directional format claims absent from the selected functional role fact."""

    return unsupported_format_directions_for_formats(mentioned_document_formats(text), facts, role)


def unsupported_format_directions_for_formats(
    formats: set[str],
    facts: ProductFactsV2 | None,
    role: FormatRole,
) -> set[str]:
    """Return named formats absent from the selected functional role fact."""

    roles = explicit_format_roles(facts)
    if not roles:
        return set()
    return {
        format_name for format_name in formats if role not in roles.get(format_name, frozenset())
    }


__all__ = [
    "FormatRole",
    "conflicting_explicit_formats",
    "explicit_format_roles",
    "formats_in_api_symbol",
    "mentioned_document_formats",
    "mentioned_explicit_formats",
    "unsupported_format_directions",
    "unsupported_format_directions_for_formats",
    "unsupported_directional_formats",
]
