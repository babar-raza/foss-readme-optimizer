"""Derive evidence-bounded input, capability, and output diagram nodes."""

from __future__ import annotations

import re
import textwrap
from typing import Literal

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_models import AgenticDiagramNodeV1
from readme_agent.readme.capability_semantics import normalize_capability_phrases
from readme_agent.readme.public_text import visitor_capability_phrase
from readme_agent.readme.public_vocabulary import DOCUMENT_FORMAT_ABBREVIATIONS

_TOKEN = re.compile(r"[a-z0-9]+")
_GENERIC_TOKENS = frozenset(
    {
        "and",
        "content",
        "data",
        "document",
        "documents",
        "file",
        "files",
        "for",
        "format",
        "formats",
        "input",
        "in",
        "object",
        "objects",
        "of",
        "on",
        "or",
        "output",
        "the",
        "to",
        "with",
    }
)
_FORBIDDEN_ROLE_SEMANTICS = re.compile(
    r"(?i)(?:\bapi\b|\bruntime\b|(?<!open-)\bsource\b|\bartifact\b"
    r"|\bmaven\b|\bnuget\b|\bpypi\b)"
)
_STRUCTURED_FORMAT = re.compile(
    r"(?i)^(load|read|import|save|write|export|supported|support|input|output)"
    r"\s+formats?\s*:\s*(.+)$"
)
_CONVERSION_CAPABILITY = re.compile(r"(?i)^(.+?)\s+to\s+(.+?)\s+conversion$")
_EXTRACTION_CAPABILITY = re.compile(r"(?i)^(.+?)\s+extraction$")
_GENERATION_CAPABILITY = re.compile(r"(?i)^(.+?)\s+generation(?:\s+with\s+.+)?$")
_BIDIRECTIONAL_CAPABILITY = re.compile(r"(?i)^(?:read\s+and\s+write|load\s+and\s+save)\s+(.+)$")
_EXTRACT_FROM_CAPABILITY = re.compile(r"(?i)^extract\s+(.+?)\s+from\s+(.+)$")
_FORMAT_IMPORT_EXPORT = re.compile(r"(?i)^file\s+format\s+import\s+and\s+export\s+for\s+(.+)$")
_INPUT_DIRECTION = re.compile(r"(?i)\b(?:import|load(?:ing)?|open|read(?:ing)?)\b")
_OUTPUT_DIRECTION = re.compile(r"(?i)\b(?:export|persist(?:ence)?|sav(?:e|ing)|writ(?:e|ing))\b")
_GENERAL_FORMAT_DIRECTION = re.compile(
    r"(?i)\b(?:file\s+formats?|formats?)\b.*"
    r"(?:import|export|load|save|read|write)"
    r"|(?:import|export|load|save|read|write).*\b(?:file\s+formats?|formats?)\b"
)


def bounded_diagram_label(value: str) -> str:
    """Return one normalized visitor label within the presentation limit."""

    normalized = " ".join(value.split())
    if len(normalized) <= 80:
        return normalized
    without_list_conjunction = normalized.replace(", and ", ", ")
    if len(without_list_conjunction) <= 80:
        return without_list_conjunction
    return textwrap.shorten(without_list_conjunction, width=80, placeholder="").rstrip(" ,;:-")


def meaningful_diagram_tokens(value: str) -> set[str]:
    """Return normalized semantic tokens used only for collision detection."""

    tokens: set[str] = set()
    for raw in _TOKEN.findall(value.casefold()):
        token = raw[:-1] if len(raw) > 4 and raw.endswith("s") else raw
        if len(token) >= 2 and token not in _GENERIC_TOKENS:
            tokens.add(token)
    return tokens


def diagram_role_identity(role: str, label: str) -> tuple[str, frozenset[str] | str]:
    """Return a role-scoped semantic identity."""

    tokens = frozenset(meaningful_diagram_tokens(label))
    return role, tokens if tokens else " ".join(label.casefold().split())


def label_has_forbidden_role_semantics(label: str) -> bool:
    """Reject infrastructure vocabulary from visitor-facing product roles."""

    if _FORBIDDEN_ROLE_SEMANTICS.search(label) is not None:
        return True
    without_domain_package_parts = re.sub(r"(?i)\bpackage\s+parts?\b", "", label)
    return re.search(r"(?i)\bpackage\b", without_domain_package_parts) is not None


def _format_label(value: str) -> str:
    normalized = value.strip().rstrip(".")
    if re.search(
        r"(?i)\b(?:file|files|workbook|workbooks|document|documents|page|pages|stream|streams)$",
        normalized,
    ):
        return normalized
    return f"{normalized} files"


def _direction_is_verified(
    facts: ProductFactsV2,
    raw_value: str,
    role: Literal["input", "output"],
    *,
    format_count: int,
) -> bool:
    """Decide direction only from accepted format or capability verbs."""

    direction = _INPUT_DIRECTION if role == "input" else _OUTPUT_DIRECTION
    if direction.search(raw_value) is not None:
        return True
    capabilities = visitor_fact_render_view(facts, "product.capabilities")
    if capabilities is None:
        return False
    for phrase in normalize_capability_phrases(capabilities.phrases):
        if direction.search(phrase) is None:
            continue
        if format_count == 1 or _GENERAL_FORMAT_DIRECTION.search(phrase) is not None:
            return True
    return False


def _directionless_format_label(value: str) -> str:
    """Keep a public diagram endpoint compact without changing fact meaning."""

    label = re.split(r"\s+-\s+", value, maxsplit=1)[0].strip()
    return _format_label(label)


def _format_node_candidates(
    facts: ProductFactsV2,
    role: Literal["input", "output"],
) -> list[AgenticDiagramNodeV1]:
    view = visitor_fact_render_view(facts, "product.formats")
    if view is None:
        return []
    fact = facts.selected_fact("product.formats")
    raw_values = fact.value if isinstance(fact.value, list) else [fact.value]
    string_values = [value for value in raw_values if isinstance(value, str) and value.strip()]
    labels: list[str] = []
    for raw_value in raw_values:
        if not isinstance(raw_value, str):
            continue
        normalized = " ".join(raw_value.split()).strip().rstrip(".")
        lowered = normalized.casefold()
        structured = _STRUCTURED_FORMAT.fullmatch(normalized)
        if structured is not None:
            operation = structured.group(1).casefold()
            allowed = (
                {"load", "read", "import", "input", "support", "supported"}
                if role == "input"
                else {"save", "write", "export", "output", "support", "supported"}
            )
            if operation not in allowed:
                continue
            candidates = [part.strip() for part in structured.group(2).split(",")]
        elif lowered.startswith(("load and save ", "read and write ")):
            prefix = "load and save " if lowered.startswith("load and save ") else "read and write "
            candidates = [normalized[len(prefix) :]]
        else:
            if not _direction_is_verified(
                facts,
                normalized,
                role,
                format_count=len(string_values),
            ):
                continue
            candidates = [_directionless_format_label(normalized)]
        for candidate in candidates:
            if not candidate or candidate.casefold() in {"auto", "automatic"}:
                continue
            label = bounded_diagram_label(_directionless_format_label(candidate))
            if label.casefold() not in {existing.casefold() for existing in labels}:
                labels.append(label)
    return [
        AgenticDiagramNodeV1(
            role=role,
            label=label,
            supporting_fact_ids=view.citation_fact_ids,
        )
        for label in labels
    ]


def _capability_flow_candidates(
    facts: ProductFactsV2,
    role: Literal["input", "output"],
    *,
    format_import_export_only: bool = False,
) -> list[AgenticDiagramNodeV1]:
    """Derive endpoints only from explicit conversion, extraction, or generation verbs."""

    view = visitor_fact_render_view(facts, "product.capabilities")
    if view is None:
        return []
    has_verified_output_formats = bool(_format_node_candidates(facts, "output"))
    candidates: list[AgenticDiagramNodeV1] = []
    for phrase in normalize_capability_phrases(view.phrases):
        normalized = " ".join(phrase.split()).rstrip(".")
        format_import_export = _FORMAT_IMPORT_EXPORT.fullmatch(normalized)
        if format_import_export is not None:
            endpoints = [
                item.strip()
                for item in re.split(r",\s*(?:and\s+)?|\s+and\s+", format_import_export.group(1))
                if item.strip()
            ]
            candidates.extend(
                AgenticDiagramNodeV1(
                    role=role,
                    label=bounded_diagram_label(_format_label(endpoint)),
                    supporting_fact_ids=view.citation_fact_ids,
                )
                for endpoint in endpoints
            )
            continue
        if format_import_export_only:
            continue
        conversion = _CONVERSION_CAPABILITY.fullmatch(normalized)
        extraction = _EXTRACTION_CAPABILITY.fullmatch(normalized)
        extract_from = _EXTRACT_FROM_CAPABILITY.fullmatch(normalized)
        generation = _GENERATION_CAPABILITY.fullmatch(normalized)
        endpoint = None
        if conversion is not None:
            endpoint = conversion.group(1 if role == "input" else 2)
        elif extract_from is not None:
            endpoint = extract_from.group(2 if role == "input" else 1)
        elif extraction is not None and role == "output":
            endpoint = extraction.group(1)
        elif generation is not None and (
            role == "output" or (role == "input" and has_verified_output_formats)
        ):
            endpoint = generation.group(1)
        if endpoint is None:
            continue
        label = (
            bounded_diagram_label(endpoint)
            if extraction is not None
            or extract_from is not None
            or generation is not None
            and role == "output"
            else bounded_diagram_label(f"{endpoint} content")
            if generation is not None
            else bounded_diagram_label(_format_label(endpoint))
        )
        candidates.append(
            AgenticDiagramNodeV1(
                role=role,
                label=label,
                supporting_fact_ids=view.citation_fact_ids,
            )
        )
    return candidates


def _directional_format_capability_candidates(
    facts: ProductFactsV2,
    role: Literal["input", "output"],
) -> list[AgenticDiagramNodeV1]:
    """Derive format endpoints only from accepted capabilities with an explicit direction."""

    view = visitor_fact_render_view(facts, "product.capabilities")
    if view is None:
        return []
    direction = _INPUT_DIRECTION if role == "input" else _OUTPUT_DIRECTION
    candidates: list[AgenticDiagramNodeV1] = []
    for phrase in normalize_capability_phrases(view.phrases):
        if direction.search(phrase) is None:
            continue
        uppercase = phrase.upper()
        formats = [
            item
            for item in DOCUMENT_FORMAT_ABBREVIATIONS
            if re.search(rf"(?<![A-Z0-9_-]){re.escape(item)}(?![A-Z0-9_-])", uppercase)
        ]
        candidates.extend(
            AgenticDiagramNodeV1(
                role=role,
                label=bounded_diagram_label(_format_label(item)),
                supporting_fact_ids=view.citation_fact_ids,
            )
            for item in formats
        )
    return candidates


def _bidirectional_capability_candidates(
    facts: ProductFactsV2,
    role: Literal["input", "output"],
) -> list[AgenticDiagramNodeV1]:
    view = visitor_fact_render_view(facts, "product.capabilities")
    if view is None:
        return []
    return [
        AgenticDiagramNodeV1(
            role=role,
            label=bounded_diagram_label(match.group(1)),
            supporting_fact_ids=view.citation_fact_ids,
        )
        for phrase in normalize_capability_phrases(view.phrases)
        if (match := _BIDIRECTIONAL_CAPABILITY.fullmatch(" ".join(phrase.split()).rstrip(".")))
        is not None
    ]


def _merge_candidates(*groups: list[AgenticDiagramNodeV1]) -> list[AgenticDiagramNodeV1]:
    merged: list[AgenticDiagramNodeV1] = []
    identities: set[tuple[str, frozenset[str] | str]] = set()
    for candidate in (item for group in groups for item in group):
        identity = diagram_role_identity(candidate.role, candidate.label)
        if identity not in identities:
            identities.add(identity)
            merged.append(candidate)
    return merged


def input_node_candidates(facts: ProductFactsV2) -> list[AgenticDiagramNodeV1]:
    """Return only evidence-backed consumed artifacts or input forms."""

    candidates = _merge_candidates(
        _format_node_candidates(facts, "input"),
        _directional_format_capability_candidates(facts, "input"),
        _capability_flow_candidates(facts, "input"),
    )
    return candidates or _bidirectional_capability_candidates(facts, "input")


def output_node_candidates(facts: ProductFactsV2) -> list[AgenticDiagramNodeV1]:
    """Return only explicitly emitted formats or action-derived results."""

    format_outputs = _format_node_candidates(facts, "output")
    candidates = _merge_candidates(
        format_outputs,
        _directional_format_capability_candidates(facts, "output"),
        _capability_flow_candidates(
            facts,
            "output",
            format_import_export_only=bool(format_outputs),
        ),
    )
    return candidates or _bidirectional_capability_candidates(facts, "output")


def selected_verified_capability_nodes(facts: ProductFactsV2) -> list[AgenticDiagramNodeV1]:
    """Return every safe selected capability in stable repository-evidence order."""

    view = visitor_fact_render_view(facts, "product.capabilities")
    if view is None:
        return []
    nodes: list[AgenticDiagramNodeV1] = []
    identities: set[tuple[str, frozenset[str] | str]] = set()
    for phrase in normalize_capability_phrases(view.phrases):
        if not phrase.strip() or label_has_forbidden_role_semantics(phrase):
            continue
        label = bounded_diagram_label(visitor_capability_phrase(phrase))
        identity = diagram_role_identity("capability", label)
        if identity in identities:
            continue
        identities.add(identity)
        nodes.append(
            AgenticDiagramNodeV1(
                role="capability",
                label=label,
                supporting_fact_ids=view.citation_fact_ids,
            )
        )
    return nodes
