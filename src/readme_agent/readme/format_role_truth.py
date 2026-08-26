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
_BIDIRECTIONAL = re.compile(
    r"(?i)^(?:load and save|read and write|import and export)\s+(?P<formats>.+)$"
)
_INPUT_OPERATIONS = frozenset({"load", "read", "import", "input"})
_OUTPUT_OPERATIONS = frozenset({"save", "write", "export", "output"})
_DIRECTIONAL_API_SUFFIX = re.compile(
    r"(?i)(?:loadoptions?|saveoptions?|importer|exporter|formatdetector|format|plugin)$"
)
_INPUT_SEMANTICS = re.compile(r"(?i)\b(?:load|open|read)s?(?:ed|ing)?\b|\.(?:open|load|read)\s*\(")
_OUTPUT_SEMANTICS = re.compile(r"(?i)\b(?:export|save|write)s?(?:ed|ing)?\b|\.(?:save|write)\s*\(")
_INPUT_LINE_PREFIX = re.compile(r"(?i)^\s*(?:#+\s*)?import(?:s|ed|ing)?\b")
_CONVERSION_LINE = re.compile(
    r"(?i)\bconvert(?:s|ed|ing)?\b(?P<input>.*?)\b(?:to|into)\b(?P<output>.+)"
)
_ROLE_FORMAT_EQUIVALENTS = {
    "DAE": "COLLADA",
    "GLB": "GLTF",
}
_AMBIGUOUS_LOWERCASE_FORMAT_WORDS = frozenset({"ONE"})


def _explicit_format_mention(text: str, format_name: str) -> bool:
    """Recognize a format term without treating an ordinary lowercase word as a format."""

    pattern = re.compile(
        rf"(?<![A-Z0-9_-]){re.escape(format_name)}(?![A-Z0-9_-])",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        if format_name not in _AMBIGUOUS_LOWERCASE_FORMAT_WORDS:
            return True
        token = match.group(0)
        if token == format_name or (match.start() > 0 and text[match.start() - 1] == "."):
            return True
    return False


def _format_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.split(r"[,;/]|\s+and\s+", value, flags=re.IGNORECASE):
        candidate = re.sub(r"(?i)\b(?:format|formats|file|files)\b", "", raw).strip(" .()")
        canonical = canonical_document_format(candidate)
        if canonical is not None:
            tokens.add(canonical)
    tokens.update(
        format_name
        for format_name in DOCUMENT_FORMAT_ABBREVIATIONS
        if _explicit_format_mention(value, format_name)
    )
    return tokens


_ROLE_BEARING_API_TYPE = re.compile(
    r"^(?P<format>[A-Za-z0-9]+?)(?P<kind>SaveOptions|LoadOptions|Exporter|Importer)$"
)
_OUTPUT_API_KINDS = frozenset({"SaveOptions", "Exporter"})


def _api_evidenced_format_roles(facts: ProductFactsV2) -> dict[str, set[FormatRole]]:
    """Return format roles the repository's own accepted public API proves.

    `product.formats` is prose the maintainer happened to write down, and it
    routinely under-reports what the package actually does: Aspose.Note's
    `product.formats` is exactly `['Input format: Microsoft OneNote (.one)']`
    while the repository ships `examples/export_pdf.py`, asserts its output
    begins with `%PDF`, compares generated PDFs against golden files, and defines
    `list(SaveFormat) == [SaveFormat.Pdf]` -- PDF export is its only output
    capability. Scoring roles from that fact alone made
    `presentation_lint_format_directions` contradict the repository itself, which
    was the single largest blocker in the 2026-08-26 fleet pass (18 occurrences,
    more than every other cause combined).

    A public `PdfSaveOptions` / `ColladaExporter` / `FbxLoadOptions` type in the
    accepted `api.public_surface` is deterministic, already-verified evidence
    that this build exposes that direction, so it is admitted as role authority.
    This only removes a false contradiction; it never adds a capability row, so a
    format cannot be advertised on the strength of a type name alone.
    """

    fact_id = facts.selected_fact_ids.get("api.public_surface")
    if fact_id is None:
        return {}
    fact = facts.fact_by_id(fact_id)
    if (
        fact.verification_state not in {"verified", "policy_approved"}
        or fact.has_unresolved_conflict
    ):
        return {}
    roles: dict[str, set[FormatRole]] = {}
    for type_name in _public_type_names(fact.value):
        match = _ROLE_BEARING_API_TYPE.match(type_name)
        if match is None:
            continue
        canonical = canonical_document_format(match.group("format"))
        if canonical is None:
            continue
        role: FormatRole = "output" if match.group("kind") in _OUTPUT_API_KINDS else "input"
        roles.setdefault(canonical, set()).add(role)
    return roles


def _public_type_names(value: object) -> set[str]:
    """Collect declared class names from an accepted API-surface fact value."""

    names: set[str] = set()
    stack: list[object] = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                names.add(name.strip())
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return names


def explicit_format_roles(facts: ProductFactsV2 | None) -> dict[str, frozenset[FormatRole]]:
    """Return role authority from ``product.formats`` plus the accepted public API.

    See `_api_evidenced_format_roles` for why the declared-formats fact alone is
    not sufficient authority.
    """

    if facts is None:
        return {}
    api_roles = _api_evidenced_format_roles(facts)
    fact_id = facts.selected_fact_ids.get("product.formats")
    if fact_id is None:
        return {name: frozenset(values) for name, values in api_roles.items()}
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return {name: frozenset(values) for name, values in api_roles.items()}
    if fact.has_unresolved_conflict or not isinstance(fact.value, list):
        return {name: frozenset(values) for name, values in api_roles.items()}
    roles: dict[str, set[FormatRole]] = {name: set(values) for name, values in api_roles.items()}
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

    return {
        format_name
        for format_name in roles
        if format_name in DOCUMENT_FORMAT_ABBREVIATIONS
        and _explicit_format_mention(text, format_name)
    }


def mentioned_document_formats(text: str) -> set[str]:
    """Return governed format abbreviations present as standalone public terms."""

    return {
        format_name
        for format_name in DOCUMENT_FORMAT_ABBREVIATIONS
        if _explicit_format_mention(text, format_name)
    }


def formats_in_api_symbol(name: str) -> set[str]:
    """Return governed formats encoded in a compact public API type name."""

    symbol = name.rsplit(".", 1)[-1].split("(", 1)[0].strip("` ")
    stem = _DIRECTIONAL_API_SUFFIX.sub("", symbol)
    canonical = canonical_document_format(stem)
    return {canonical} if canonical is not None else set()


def _formats_in_line(line: str) -> set[str]:
    formats = mentioned_document_formats(line)
    for identifier in re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", line):
        formats.update(formats_in_api_symbol(identifier))
    return formats


def directional_format_claims(text: str) -> dict[FormatRole, frozenset[str]]:
    """Return the explicit format roles asserted by one public fragment."""

    claims: dict[FormatRole, set[str]] = {"input": set(), "output": set()}
    for line in text.splitlines():
        conversion = _CONVERSION_LINE.search(line)
        if conversion is not None:
            claims["input"].update(_formats_in_line(conversion.group("input")))
            claims["output"].update(_formats_in_line(conversion.group("output")))
            continue
        formats = _formats_in_line(line)
        if _INPUT_LINE_PREFIX.search(line) or _INPUT_SEMANTICS.search(line):
            claims["input"].update(formats)
        if _OUTPUT_SEMANTICS.search(line):
            claims["output"].update(formats)
    return {role: frozenset(values) for role, values in claims.items() if values}


def unsupported_directional_formats(
    text: str,
    facts: ProductFactsV2 | None,
) -> dict[FormatRole, frozenset[str]]:
    """Return unsupported input/output claims made by one public fragment."""

    claims = {
        role: frozenset(unsupported_format_directions_for_formats(set(formats), facts, role))
        for role, formats in directional_format_claims(text).items()
    }
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
        format_name
        for format_name in formats
        if role
        not in roles.get(_ROLE_FORMAT_EQUIVALENTS.get(format_name, format_name), frozenset())
    }


__all__ = [
    "FormatRole",
    "conflicting_explicit_formats",
    "directional_format_claims",
    "explicit_format_roles",
    "formats_in_api_symbol",
    "mentioned_document_formats",
    "mentioned_explicit_formats",
    "unsupported_format_directions",
    "unsupported_format_directions_for_formats",
    "unsupported_directional_formats",
]
