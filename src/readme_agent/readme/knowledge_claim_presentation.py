"""Render verified imported-knowledge items as bounded public README content."""

from __future__ import annotations

import re
from dataclasses import dataclass

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.public_text import canonicalize_public_markdown
from readme_agent.readme.public_vocabulary import canonical_abbreviations_from_facts

_KNOWLEDGE_FIELDS = frozenset(
    {
        "aspose.feature_claims",
        "aspose.format_support_claims",
        "aspose.install_claims",
        "aspose.limitation_claims",
        "aspose.troubleshoot_claims",
    }
)
_INTERNAL_ASSURANCE = re.compile(
    r"(?i)\b(?:acceptance|agent(?:ic)?|cache|candidate|checksum|corroborat|evidence|fixture|"
    r"gate|inventory|llm|manifest|no[- ]op|provenance|receipt|revision|snapshot|"
    r"source[- ]tree|validation|verif(?:y|ied|ication))\b"
)
_PATH_OR_LOCATION = re.compile(
    r"(?:^|\s)(?:[A-Za-z]:[\\/]|(?:src|tests?|docs?|scripts?)/)[^\s`]+|:\d+(?:\b|$)",
    re.IGNORECASE,
)
_FORMAT_SUPPORT = re.compile(
    r"(?i)^(?P<action>export|import) support for (?P<format>[A-Za-z0-9_+.-]+)"
    r"(?: format)?(?: via (?P<api>[A-Za-z0-9_.]+)|"
    r" \(method name: (?P<method>[A-Za-z0-9_]+)\))$"
)
_FORMAT_DETECTION = re.compile(
    r"(?i)^detects format (?P<format>[A-Za-z0-9_+.-]+) via (?P<api>[A-Za-z0-9_.]+)$"
)
_NOT_IMPLEMENTED = re.compile(
    r"(?i)^not implemented:\s*(?P<symbol>[A-Za-z_][A-Za-z0-9_.]*)"
    r"(?:\s+in\s+.+:\d+)?$"
)
_UNIMPLEMENTED_STUB = re.compile(
    r"(?i)^unimplemented stub \(empty body\):\s*(?P<symbol>[A-Za-z_][A-Za-z0-9_.]*)"
    r"\s+in\s+.+:\d+$"
)
_UNAVAILABLE_SYMBOL_CONTEXT = re.compile(
    r"(?i)\b(?:not\s+(?:yet\s+)?implemented|unsupported|"
    r"throw(?:s|ing)?\b.{0,80}\bUnsupportedOperationException)\b"
)
_BACKTICK_DOTTED_SYMBOL = re.compile(
    r"`(?P<symbol>[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)`"
)
_LIMITATION_CLAUSE_BOUNDARY = re.compile(
    r"[;.]\s+|,\s+(?=(?:but|whereas|while)\b)|\b(?:but|whereas|while)\b",
    re.IGNORECASE,
)
_INSTALL_NAME = re.compile(r"(?i)^package name is (?P<value>\S+)$")
_INSTALL_VERSION = re.compile(r"(?i)^current version is (?P<value>[A-Za-z0-9_.+-]+)$")
_ACTION_LED = re.compile(
    r"(?i)^(?:add|build|check|configure|convert|create|decode|detect|encode|export|"
    r"extract|generate|handle|import|inspect|load|manage|open|parse|process|read|"
    r"render|run|save|support|transform|use|validate|write)\b"
)
_FEATURE_DETAIL = re.compile(
    r"(?i)^(?P<title>.+?)\s+(?P<link>using|via|with|for)\s+(?P<detail>.+)$"
)


@dataclass(frozen=True)
class KnowledgePresentationItem:
    """One exact selected item and the visitor-facing Markdown it authorizes."""

    fact_id: str
    field: str
    source_value: dict[str, object]
    markdown: str


def _selected_fact(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    try:
        fact = facts.selected_fact(field)
    except KeyError:
        return None
    if (
        fact.verification_state not in {"verified", "policy_approved"}
        or fact.has_unresolved_conflict
        or not isinstance(fact.value, list)
    ):
        return None
    return fact


def _source_items(
    facts: ProductFactsV2,
    field: str,
) -> list[tuple[FactRecordV2, dict[str, object]]]:
    fact = _selected_fact(facts, field)
    if fact is None:
        return []
    return [
        (fact, item)
        for item in fact.value
        if isinstance(item, dict)
        and isinstance(item.get("claim_id"), str)
        and isinstance(item.get("text"), str)
    ]


def _canonical(facts: ProductFactsV2, text: str) -> str:
    return canonicalize_public_markdown(text, canonical_abbreviations_from_facts(facts))


def _public_sentence(text: str) -> str | None:
    normalized = " ".join(text.strip().split())
    if (
        not normalized
        or len(normalized) > 240
        or _INTERNAL_ASSURANCE.search(normalized)
        or _PATH_OR_LOCATION.search(normalized)
        or any(token in normalized for token in ("{", "}", "[REDACTED]"))
    ):
        return None
    return normalized.rstrip(". ") + "."


def _code(value: str) -> str:
    suffix = "()" if re.fullmatch(r"[a-z_][a-z0-9_]*", value) else ""
    return f"`{value}{suffix}`"


def _format_markdown(facts: ProductFactsV2, text: str) -> str | None:
    match = _FORMAT_SUPPORT.fullmatch(text.strip())
    if match is not None:
        action = match.group("action").casefold()
        format_name = _canonical(facts, match.group("format"))
        api = match.group("api") or match.group("method")
        verb = "Export to" if action == "export" else "Import"
        direction = "output" if action == "export" else "input"
        return f"- **{verb} {format_name}** - Handle {format_name} {direction} with {_code(api)}."
    match = _FORMAT_DETECTION.fullmatch(text.strip())
    if match is None:
        return None
    format_name = _canonical(facts, match.group("format"))
    return (
        f"- **Detect {format_name} files** - Identify {format_name} input with "
        f"{_code(match.group('api'))}."
    )


def _feature_markdown(facts: ProductFactsV2, text: str) -> str | None:
    sentence = _public_sentence(text)
    if sentence is None:
        return None
    body = sentence.rstrip(".")
    if not _ACTION_LED.match(body):
        return None
    detail = _FEATURE_DETAIL.fullmatch(body)
    if detail is None or len(detail.group("title").split()) > 10:
        return None
    title = detail.group("title").rstrip(". ")
    explanation = f"{detail.group('link').capitalize()} {detail.group('detail').rstrip('. ')}."
    return _canonical(facts, f"- **{title}** - {explanation}")


def knowledge_capability_items(facts: ProductFactsV2) -> tuple[KnowledgePresentationItem, ...]:
    """Return bounded feature and format rows with their exact source items."""

    rendered: list[KnowledgePresentationItem] = []
    for field, renderer in (
        ("aspose.feature_claims", _feature_markdown),
        ("aspose.format_support_claims", _format_markdown),
    ):
        for fact, item in _source_items(facts, field):
            markdown = renderer(facts, str(item["text"]))
            if markdown is not None:
                rendered.append(KnowledgePresentationItem(fact.fact_id, field, item, markdown))
    return tuple(rendered)


def knowledge_limitation_items(facts: ProductFactsV2) -> tuple[KnowledgePresentationItem, ...]:
    """Remove source locations while retaining exact public limitation semantics."""

    rendered: list[KnowledgePresentationItem] = []
    for fact, item in _source_items(facts, "aspose.limitation_claims"):
        text = str(item["text"])
        match = _NOT_IMPLEMENTED.fullmatch(text.strip()) or _UNIMPLEMENTED_STUB.fullmatch(
            text.strip()
        )
        if match is not None and not match.group("symbol").endswith("."):
            public = f"- `{match.group('symbol')}` is not implemented in this FOSS package."
        else:
            sentence = _public_sentence(text)
            if sentence is None:
                continue
            public = f"- {_canonical(facts, sentence)}"
        rendered.append(KnowledgePresentationItem(fact.fact_id, fact.field, item, public))
    return tuple(rendered)


def knowledge_unimplemented_symbols(facts: ProductFactsV2) -> frozenset[str]:
    """Return exact accepted API symbols whose implementation is unavailable."""

    symbols: set[str] = set()
    for _fact, item in _source_items(facts, "aspose.limitation_claims"):
        text = str(item["text"])
        match = _NOT_IMPLEMENTED.fullmatch(text.strip()) or _UNIMPLEMENTED_STUB.fullmatch(
            text.strip()
        )
        if match is not None and "." in match.group("symbol"):
            symbols.add(match.group("symbol").casefold())
    try:
        limitation = facts.selected_fact("product.limitations")
    except KeyError:
        limitation = None
    if (
        limitation is not None
        and limitation.verification_state in {"verified", "policy_approved"}
        and not limitation.has_unresolved_conflict
    ):
        values = limitation.value if isinstance(limitation.value, list) else [limitation.value]
        for value in values:
            if not isinstance(value, str):
                continue
            for clause in _LIMITATION_CLAUSE_BOUNDARY.split(value):
                if _UNAVAILABLE_SYMBOL_CONTEXT.search(clause) is not None:
                    symbols.update(
                        match.group("symbol").casefold()
                        for match in _BACKTICK_DOTTED_SYMBOL.finditer(clause)
                    )
    return frozenset(symbols)


def _verified_coordinate_values(facts: ProductFactsV2) -> tuple[set[str], set[str]]:
    names: set[str] = set()
    versions: set[str] = set()
    for field in ("installation.coordinates", "installation.verified_acquisition"):
        try:
            fact = facts.selected_fact(field)
        except KeyError:
            continue
        if fact.verification_state not in {"verified", "policy_approved"}:
            continue
        values = fact.value if isinstance(fact.value, list) else [fact.value]
        for value in values:
            if not isinstance(value, dict):
                continue
            nested_coordinate = value.get("coordinate")
            coordinate: dict[str, object] = (
                nested_coordinate if isinstance(nested_coordinate, dict) else value
            )
            for key in ("name", "artifact_id"):
                if coordinate.get(key):
                    names.add(str(coordinate[key]).casefold())
            if coordinate.get("version"):
                versions.add(str(coordinate["version"]).casefold())
            if value.get("version"):
                versions.add(str(value["version"]).casefold())
    return names, versions


def knowledge_installation_items(facts: ProductFactsV2) -> tuple[KnowledgePresentationItem, ...]:
    """Render only package metadata that exactly agrees with verified acquisition facts."""

    names, versions = _verified_coordinate_values(facts)
    rendered: list[KnowledgePresentationItem] = []
    for fact, item in _source_items(facts, "aspose.install_claims"):
        text = str(item["text"]).strip()
        name = _INSTALL_NAME.fullmatch(text)
        version = _INSTALL_VERSION.fullmatch(text)
        if name is not None and name.group("value").casefold() in names:
            markdown = f"- Package: `{name.group('value')}`"
        elif version is not None and version.group("value").casefold() in versions:
            markdown = f"- Version: `{version.group('value')}`"
        else:
            continue
        rendered.append(KnowledgePresentationItem(fact.fact_id, fact.field, item, markdown))
    return tuple(rendered)


def knowledge_troubleshooting_items(
    facts: ProductFactsV2,
) -> tuple[KnowledgePresentationItem, ...]:
    """Return public, action-led troubleshooting guidance without internal notes."""

    rendered: list[KnowledgePresentationItem] = []
    for fact, item in _source_items(facts, "aspose.troubleshoot_claims"):
        sentence = _public_sentence(str(item["text"]))
        if sentence is None or not _ACTION_LED.match(sentence):
            continue
        rendered.append(
            KnowledgePresentationItem(
                fact.fact_id,
                fact.field,
                item,
                f"- {_canonical(facts, sentence)}",
            )
        )
    return tuple(rendered)


def rendered_knowledge_coordinates(
    claim_text: str,
    facts: ProductFactsV2,
    fact_ids: set[str],
) -> tuple[KnowledgePresentationItem, ...]:
    """Return exact knowledge items whose deterministic Markdown equals this claim."""

    normalized = claim_text.strip()
    items = (
        *knowledge_capability_items(facts),
        *knowledge_limitation_items(facts),
        *knowledge_installation_items(facts),
        *knowledge_troubleshooting_items(facts),
    )
    return tuple(
        item for item in items if item.fact_id in fact_ids and item.markdown.strip() == normalized
    )


__all__ = [
    "KnowledgePresentationItem",
    "knowledge_capability_items",
    "knowledge_installation_items",
    "knowledge_limitation_items",
    "knowledge_unimplemented_symbols",
    "knowledge_troubleshooting_items",
    "rendered_knowledge_coordinates",
]
