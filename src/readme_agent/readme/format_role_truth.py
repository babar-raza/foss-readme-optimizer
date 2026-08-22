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


__all__ = [
    "FormatRole",
    "conflicting_explicit_formats",
    "explicit_format_roles",
    "mentioned_explicit_formats",
]
