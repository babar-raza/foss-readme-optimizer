"""Enforce visitor-facing fact semantics for README diagram roles."""

from __future__ import annotations

import re
import textwrap
from collections.abc import Iterable
from typing import Literal, cast

from readme_agent.errors import LLMError
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_models import AgenticDiagramNodeV1

_ROLE_FACT_FIELD_ORDER = {
    "input": ("product.formats", "product.capabilities", "product.problems_solved"),
    "capability": ("product.capabilities", "product.problems_solved", "product.formats"),
    "output": ("product.formats", "product.capabilities", "product.problems_solved"),
}
_ROLE_FACT_FIELDS = {role: frozenset(fields) for role, fields in _ROLE_FACT_FIELD_ORDER.items()}
_TOKEN = re.compile(r"[a-z0-9]+")
_GENERIC_TOKENS = frozenset(
    {
        "and",
        "content",
        "data",
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


def _bounded_label(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= 80:
        return normalized
    without_list_conjunction = normalized.replace(", and ", ", ")
    if len(without_list_conjunction) <= 80:
        return without_list_conjunction
    return textwrap.shorten(without_list_conjunction, width=80, placeholder="")


def _canonical_label(value: str) -> str:
    return " ".join(value.casefold().split())


def _meaningful_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for raw in _TOKEN.findall(value.casefold()):
        token = raw[:-1] if len(raw) > 4 and raw.endswith("s") else raw
        if len(token) >= 2 and token not in _GENERIC_TOKENS:
            tokens.add(token)
    return tokens


def _role_identity(role: str, label: str) -> tuple[str, frozenset[str] | str]:
    tokens = frozenset(_meaningful_tokens(label))
    return role, tokens if tokens else _canonical_label(label)


def _node_has_literal_fact_grounding(node: AgenticDiagramNodeV1, facts: ProductFactsV2) -> bool:
    label_tokens = _meaningful_tokens(node.label)
    if not label_tokens:
        return False
    fact_tokens: set[str] = set()
    for fact_id in node.supporting_fact_ids:
        field = facts.fact_by_id(fact_id).field
        view = visitor_fact_render_view(facts, field)
        if view is not None:
            for phrase in view.phrases:
                fact_tokens.update(_meaningful_tokens(phrase))
    return bool(label_tokens) and label_tokens <= fact_tokens


def _label_has_forbidden_role_semantics(label: str) -> bool:
    if _FORBIDDEN_ROLE_SEMANTICS.search(label) is not None:
        return True
    without_domain_package_parts = re.sub(r"(?i)\bpackage\s+parts?\b", "", label)
    return re.search(r"(?i)\bpackage\b", without_domain_package_parts) is not None


def _format_label(value: str) -> str:
    normalized = value.strip().rstrip(".")
    if re.search(
        r"(?i)\b(?:file|files|workbook|workbooks|document|documents|stream|streams)$", normalized
    ):
        return normalized
    return f"{normalized} files"


def _format_node_candidates(
    facts: ProductFactsV2,
    role: Literal["input", "output"],
) -> list[AgenticDiagramNodeV1]:
    view = visitor_fact_render_view(facts, "product.formats")
    if view is None:
        return []
    fact = facts.selected_fact("product.formats")
    raw_values = fact.value if isinstance(fact.value, list) else [fact.value]
    labels: list[str] = []
    for raw_value in raw_values:
        if not isinstance(raw_value, str):
            continue
        phrase = raw_value
        normalized = " ".join(phrase.split()).strip().rstrip(".")
        lowered = normalized.casefold()
        candidates: list[str]
        structured = _STRUCTURED_FORMAT.fullmatch(normalized)
        if structured is not None:
            operation = structured.group(1).casefold()
            input_operations = {"load", "read", "import", "input", "support", "supported"}
            output_operations = {"save", "write", "export", "output", "support", "supported"}
            if role == "input" and operation not in input_operations:
                continue
            if role == "output" and operation not in output_operations:
                continue
            candidates = [part.strip() for part in structured.group(2).split(",")]
        elif lowered.startswith("load and save "):
            candidates = [normalized[len("load and save ") :]]
        elif lowered.startswith("read and write "):
            candidates = [normalized[len("read and write ") :]]
        else:
            candidates = [normalized]
        for candidate in candidates:
            if not candidate or candidate.casefold() in {"auto", "automatic"}:
                continue
            label = _format_label(candidate)
            if label.casefold() not in {existing.casefold() for existing in labels}:
                labels.append(_bounded_label(label))
    return [
        AgenticDiagramNodeV1(
            role=role,
            label=label,
            supporting_fact_ids=view.citation_fact_ids,
        )
        for label in labels
    ]


def _input_node_candidates(facts: ProductFactsV2) -> list[AgenticDiagramNodeV1]:
    return _merge_role_candidates(
        _format_node_candidates(facts, "input"),
        _capability_flow_candidates(facts, "input"),
    )


def _output_node_candidates(facts: ProductFactsV2) -> list[AgenticDiagramNodeV1]:
    return _merge_role_candidates(
        _format_node_candidates(facts, "output"),
        _capability_flow_candidates(facts, "output"),
    )


_CONVERSION_CAPABILITY = re.compile(r"(?i)^(.+?)\s+to\s+(.+?)\s+conversion$")
_EXTRACTION_CAPABILITY = re.compile(r"(?i)^(.+?)\s+extraction$")
_GENERATION_CAPABILITY = re.compile(r"(?i)^(.+?)\s+generation(?:\s+with\s+.+)?$")


def _capability_flow_candidates(
    facts: ProductFactsV2,
    role: Literal["input", "output"],
) -> list[AgenticDiagramNodeV1]:
    """Derive literal flow endpoints from verified conversion/extraction capabilities."""

    view = visitor_fact_render_view(facts, "product.capabilities")
    if view is None:
        return []
    candidates: list[AgenticDiagramNodeV1] = []
    for phrase in view.phrases:
        conversion = _CONVERSION_CAPABILITY.fullmatch(" ".join(phrase.split()).rstrip("."))
        extraction = _EXTRACTION_CAPABILITY.fullmatch(" ".join(phrase.split()).rstrip("."))
        generation = _GENERATION_CAPABILITY.fullmatch(" ".join(phrase.split()).rstrip("."))
        endpoint = None
        if conversion is not None:
            endpoint = conversion.group(1 if role == "input" else 2)
        elif extraction is not None and role == "output":
            endpoint = extraction.group(1)
        elif generation is not None and role == "input":
            endpoint = generation.group(1)
        if endpoint is None:
            continue
        candidates.append(
            AgenticDiagramNodeV1(
                role=role,
                label=(
                    _bounded_label(endpoint)
                    if extraction is not None
                    else _bounded_label(f"{endpoint} content")
                    if generation is not None
                    else _format_label(endpoint)
                ),
                supporting_fact_ids=view.citation_fact_ids,
            )
        )
    return candidates


def _merge_role_candidates(*groups: list[AgenticDiagramNodeV1]) -> list[AgenticDiagramNodeV1]:
    merged: list[AgenticDiagramNodeV1] = []
    token_sets: list[set[str]] = []
    for candidate in (item for group in groups for item in group):
        tokens = _meaningful_tokens(candidate.label)
        duplicate_index = next(
            (index for index, existing in enumerate(token_sets) if existing == tokens),
            None,
        )
        if duplicate_index is None:
            token_sets.append(tokens)
            merged.append(candidate)
            continue
        existing = merged[duplicate_index]
        merged[duplicate_index] = existing.model_copy(
            update={
                "supporting_fact_ids": list(
                    dict.fromkeys([*existing.supporting_fact_ids, *candidate.supporting_fact_ids])
                )
            }
        )
    return merged


def selected_verified_capability_nodes(facts: ProductFactsV2) -> list[AgenticDiagramNodeV1]:
    """Return every safe selected capability in stable repository-evidence order."""

    view = visitor_fact_render_view(facts, "product.capabilities")
    if view is None:
        return []
    nodes: list[AgenticDiagramNodeV1] = []
    identities: set[tuple[str, frozenset[str] | str]] = set()
    for phrase in view.phrases:
        if not phrase.strip() or _label_has_forbidden_role_semantics(phrase):
            continue
        label = _bounded_label(phrase)
        identity = _role_identity("capability", label)
        if identity in identities:
            continue
        candidate = AgenticDiagramNodeV1(
            role="capability",
            label=label,
            supporting_fact_ids=view.citation_fact_ids,
        )
        if _node_semantic_error(candidate, facts) is not None:
            continue
        identities.add(identity)
        nodes.append(candidate)
    return nodes


def _node_semantic_error(node: AgenticDiagramNodeV1, facts: ProductFactsV2) -> str | None:
    try:
        cited_fields = sorted(
            {facts.fact_by_id(fact_id).field for fact_id in node.supporting_fact_ids}
        )
    except KeyError:
        return None
    disallowed = [field for field in cited_fields if field not in _ROLE_FACT_FIELDS[node.role]]
    if disallowed:
        return f"{node.role}:{node.label!r} cites {disallowed}"
    if _label_has_forbidden_role_semantics(node.label):
        return f"{node.role}:{node.label!r} describes an API, runtime, source, or package surface"
    if node.role == "input":
        allowed_labels = {
            " ".join(candidate.label.casefold().split())
            for candidate in _input_node_candidates(facts)
        }
        if " ".join(node.label.casefold().split()) not in allowed_labels:
            return f"input:{node.label!r} is not a declared source format or input form"
    if node.role == "output" and "product.formats" in cited_fields:
        allowed_labels = {
            " ".join(candidate.label.casefold().split())
            for candidate in _output_node_candidates(facts)
        }
        if " ".join(node.label.casefold().split()) not in allowed_labels:
            return f"output:{node.label!r} is not a declared result format or output form"
    if not _node_has_literal_fact_grounding(node, facts):
        return f"{node.role}:{node.label!r} is not grounded in its cited fact text"
    return None


def normalize_diagram_role_nodes(
    nodes: Iterable[AgenticDiagramNodeV1],
    facts: ProductFactsV2,
    required_counts: dict[str, int],
    target_counts: dict[str, int] | None = None,
) -> list[AgenticDiagramNodeV1]:
    """Replace invalid or missing role nodes with literal accepted fact phrases."""

    normalized: list[AgenticDiagramNodeV1] = []
    positions: dict[tuple[str, frozenset[str] | str], int] = {}
    for node in nodes:
        if _node_semantic_error(node, facts) is not None:
            continue
        if node.role in {"input", "output"}:
            role_candidates = (
                _input_node_candidates(facts)
                if node.role == "input"
                else _output_node_candidates(facts)
            )
            canonical = next(
                (
                    candidate
                    for candidate in role_candidates
                    if _role_identity(candidate.role, candidate.label)
                    == _role_identity(node.role, node.label)
                ),
                None,
            )
            if canonical is not None:
                node = node.model_copy(
                    update={
                        "label": canonical.label,
                        "supporting_fact_ids": list(
                            dict.fromkeys(
                                [*node.supporting_fact_ids, *canonical.supporting_fact_ids]
                            )
                        ),
                    }
                )
        identity = _role_identity(node.role, node.label)
        existing_index = positions.get(identity)
        if existing_index is None:
            positions[identity] = len(normalized)
            normalized.append(node)
            continue
        existing = normalized[existing_index]
        normalized[existing_index] = existing.model_copy(
            update={
                "supporting_fact_ids": list(
                    dict.fromkeys([*existing.supporting_fact_ids, *node.supporting_fact_ids])
                )
            }
        )
    capability_view = visitor_fact_render_view(facts, "product.capabilities")
    if capability_view is not None:
        for capability in selected_verified_capability_nodes(facts):
            capability_label = capability.label
            if any(
                node.role == "capability"
                and " ".join(node.label.casefold().split())
                == " ".join(capability_label.casefold().split())
                for node in normalized
            ):
                continue
            normalized.append(
                AgenticDiagramNodeV1(
                    role="capability",
                    label=capability_label,
                    supporting_fact_ids=capability.supporting_fact_ids,
                )
            )
    capability_fact_fields = ("product.capabilities", "product.problems_solved")
    for field in capability_fact_fields:
        view = visitor_fact_render_view(facts, field)
        if view is None or any(
            node.role == "capability"
            and set(node.supporting_fact_ids).intersection(view.citation_fact_ids)
            for node in normalized
        ):
            continue
        representative = next(
            (
                _bounded_label(phrase)
                for phrase in view.phrases
                if phrase.strip() and not _label_has_forbidden_role_semantics(phrase)
            ),
            None,
        )
        if representative is None:
            continue
        duplicate_index = next(
            (
                index
                for index, node in enumerate(normalized)
                if node.role == "capability"
                and " ".join(node.label.casefold().split())
                == " ".join(representative.casefold().split())
            ),
            None,
        )
        if duplicate_index is not None:
            duplicate = normalized[duplicate_index]
            normalized[duplicate_index] = duplicate.model_copy(
                update={
                    "supporting_fact_ids": list(
                        dict.fromkeys([*duplicate.supporting_fact_ids, *view.citation_fact_ids])
                    )
                }
            )
        else:
            normalized.append(
                AgenticDiagramNodeV1(
                    role="capability",
                    label=representative,
                    supporting_fact_ids=view.citation_fact_ids,
                )
            )
    output_formats = _output_node_candidates(facts)
    if output_formats and not any(
        node.role == "output"
        and "product.formats"
        in {facts.fact_by_id(fact_id).field for fact_id in node.supporting_fact_ids}
        for node in normalized
    ):
        candidate = output_formats[0]
        candidate_identity = _role_identity(candidate.role, candidate.label)
        duplicate_index = next(
            (
                index
                for index, node in enumerate(normalized)
                if _role_identity(node.role, node.label) == candidate_identity
            ),
            None,
        )
        if duplicate_index is None:
            normalized.append(candidate)
        else:
            duplicate = normalized[duplicate_index]
            normalized[duplicate_index] = duplicate.model_copy(
                update={
                    "supporting_fact_ids": list(
                        dict.fromkeys(
                            [*duplicate.supporting_fact_ids, *candidate.supporting_fact_ids]
                        )
                    )
                }
            )
    identities_by_role = {
        role: {_role_identity(role, node.label) for node in normalized if node.role == role}
        for role in required_counts
    }
    for role, minimum in required_counts.items():
        desired = (target_counts or required_counts).get(role, minimum)
        current = sum(node.role == role for node in normalized)
        if current >= desired:
            continue
        if role == "input":
            candidates = _input_node_candidates(facts)
        elif role == "output":
            candidates = _output_node_candidates(facts)
        else:
            candidates = []
            for field in _ROLE_FACT_FIELD_ORDER[role]:
                view = visitor_fact_render_view(facts, field)
                if view is None:
                    continue
                candidates.extend(
                    AgenticDiagramNodeV1(
                        role=cast(Literal["input", "capability", "output"], role),
                        label=_bounded_label(phrase),
                        supporting_fact_ids=view.citation_fact_ids,
                    )
                    for phrase in view.phrases
                    if phrase.strip()
                )
        for candidate in candidates:
            identity = _role_identity(role, candidate.label)
            if (
                not candidate.label
                or identity in identities_by_role[role]
                or _node_semantic_error(candidate, facts) is not None
            ):
                continue
            normalized.append(candidate)
            identities_by_role[role].add(identity)
            current += 1
            if current >= desired:
                break
    return normalized


def diagram_role_phrase_guidance(facts: ProductFactsV2) -> dict[str, list[str]]:
    """Return a compact literal vocabulary for one bounded authoring repair."""

    guidance: dict[str, list[str]] = {}
    for role, fields in _ROLE_FACT_FIELD_ORDER.items():
        if role == "input":
            guidance[role] = [node.label for node in _input_node_candidates(facts)]
            continue
        phrases: list[str] = []
        for field in sorted(fields):
            view = visitor_fact_render_view(facts, field)
            if view is None:
                continue
            if role == "output" and field == "product.formats":
                for candidate in _output_node_candidates(facts):
                    if candidate.label not in phrases:
                        phrases.append(candidate.label)
                continue
            for phrase in view.phrases:
                normalized = textwrap.shorten(" ".join(phrase.split()), width=160, placeholder="")
                if (
                    normalized
                    and not _label_has_forbidden_role_semantics(normalized)
                    and normalized not in phrases
                ):
                    phrases.append(normalized)
        guidance[role] = phrases if role == "capability" else phrases[:12]
    return guidance


def validate_diagram_role_fact_semantics(
    nodes: Iterable[AgenticDiagramNodeV1],
    facts: ProductFactsV2,
) -> None:
    """Reject infrastructure or acquisition evidence posed as product flow semantics."""

    invalid: list[str] = []
    for node in nodes:
        error = _node_semantic_error(node, facts)
        if error is not None:
            invalid.append(error)
    if invalid:
        raise LLMError(
            "composition diagram assigns infrastructure or non-product facts to visitor roles: "
            + "; ".join(invalid)
        )
