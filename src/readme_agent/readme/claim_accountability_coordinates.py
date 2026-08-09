"""Derive exact visitor-meaningful coordinates from selected structured facts."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from functools import lru_cache

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import (
    ReadmeMaterialClaimAssessmentV1,
    assess_material_claims,
)
from readme_agent.readme.claim_accountability_api_coordinates import (
    api_structured_fact_coordinates,
)
from readme_agent.readme.claim_accountability_golden_workflow_coordinates import (
    golden_workflow_fact_coordinates,
)
from readme_agent.readme.claim_accountability_installation_coordinates import (
    python_source_build_distribution_coordinates,
)
from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.document_templates import installation_text
from readme_agent.readme.public_limitations import public_limitation_fact_coordinates
from readme_agent.readme.python_install_target import (
    normalized_python_distribution,
    parse_python_optional_extras_install,
    selected_python_install_target,
)

_VERIFIED_INPUT = re.compile(
    r"(?is)^\s*-\s*(?:Before running the example,\s*)?provide\s+`(?P<target>[^`]+)`;\s*"
    r"verification used the repository fixture\s*"
    r"`(?P<source>[^`]+)`\.\s*$"
)
_FORMAT_DIRECTION_MARKER = re.compile(
    r"(?i)\b(?P<input>read(?:s|ing)?|load(?:s|ing)?|import(?:s|ing)?|"
    r"open(?:s|ing)?|accept(?:s|ing)?|input|source)|"
    r"\b(?P<output>write(?:s|ing)?|save(?:s|ing)?|export(?:s|ing)?|"
    r"produce(?:s|d|ing)?|output|destination)\b"
)


def _format_role_is_explicit(text: str, visible_item: str, role: str) -> bool:
    """Require a local directional cue before binding an input/output format."""

    normalized = " ".join(re.sub(r"[`*_~]", "", text).casefold().split())
    item = " ".join(visible_item.casefold().split())
    if not item:
        return False
    for occurrence in re.finditer(rf"(?<![a-z0-9]){re.escape(item)}(?![a-z0-9])", normalized):
        clause_start = max(
            normalized.rfind(separator, 0, occurrence.start()) for separator in (".", ";", "\n")
        )
        clause = normalized[clause_start + 1 : occurrence.end()]
        conversion_input = re.search(
            rf"\bconvert(?:s|ed|ing)?\b[^.;]{{0,120}}"
            rf"(?<![a-z0-9]){re.escape(item)}(?![a-z0-9])[^.;]{{0,80}}\bto\b",
            clause,
        )
        conversion_output = re.search(
            rf"\b(?:convert(?:s|ed|ing)?|render(?:s|ed|ing)?)\b"
            rf"[^.;]{{0,160}}\bto\b[^.;]{{0,80}}"
            rf"(?<![a-z0-9]){re.escape(item)}(?![a-z0-9])",
            clause,
        )
        if role == "input" and conversion_input is not None:
            return True
        if role == "output" and conversion_output is not None:
            return True
        markers = list(_FORMAT_DIRECTION_MARKER.finditer(clause[: occurrence.end()]))
        if not markers:
            continue
        latest = markers[-1]
        latest_role = "input" if latest.group("input") is not None else "output"
        if latest_role == role and occurrence.end() - latest.start() <= 160:
            return True
    return False


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _coordinate(
    *, fact_id: str, field: str, path: str, value: object
) -> StructuredFactCoordinateV1:
    return StructuredFactCoordinateV1(
        fact_id=fact_id,
        field=field,
        path=path,
        value_sha256=_canonical_sha256(value),
    )


@lru_cache(maxsize=32)
def _document_bytes(document: str) -> bytes:
    return document.encode("utf-8")


@lru_cache(maxsize=32)
def _document_headings(document: str):
    return tuple(parse_headings(document))


@lru_cache(maxsize=64)
def _material_claim_texts(document: str) -> frozenset[str]:
    encoded = _document_bytes(document)
    return frozenset(
        encoded[claim.source_byte_start : claim.source_byte_end].decode("utf-8").strip()
        for claim in assess_material_claims(document)
    )


def _claim_character_start(document: str, claim: ReadmeMaterialClaimAssessmentV1) -> int:
    return len(_document_bytes(document)[: claim.source_byte_start].decode("utf-8"))


def _claim_context(document: str, claim: ReadmeMaterialClaimAssessmentV1) -> str:
    character_start = _claim_character_start(document, claim)
    context = [
        heading.title
        for heading in _document_headings(document)
        if heading.heading_end <= character_start < heading.section_end
    ]
    line_start = document.rfind("\n", 0, character_start) + 1
    current_line = document[line_start : document.find("\n", line_start)]
    current_indent = len(current_line) - len(current_line.lstrip())
    if current_indent:
        prior_lines = document[:line_start].splitlines()
        for line in reversed(prior_lines):
            match = re.match(r"^(?P<indent>\s*)[-+*]\s+(?P<body>.+)$", line)
            if match is not None and len(match.group("indent")) < current_indent:
                context.append(match.group("body"))
                break
    return "\n".join(context)


def _optional_extra_coordinates(
    text: str,
    facts: ProductFactsV2,
    fact_id: str,
    value: object,
) -> list[StructuredFactCoordinateV1]:
    parsed = parse_python_optional_extras_install(text)
    if parsed is None or not isinstance(value, dict) or not isinstance(value.get("extras"), dict):
        return []
    target_policy = selected_python_install_target(facts)
    if target_policy is None:
        return []
    target, extras = parsed
    if normalized_python_distribution(target) != normalized_python_distribution(
        target_policy.target
    ) or any(extra not in value["extras"] for extra in extras):
        return []
    return [
        _coordinate(
            fact_id=fact_id,
            field="installation.optional_extras",
            path=f"/extras/{extra}",
            value={"extra": extra, "dependencies": value["extras"][extra]},
        )
        for extra in extras
    ]


def _exact_list_coordinates(
    text: str, fact_id: str, field: str, value: object
) -> list[StructuredFactCoordinateV1]:
    if not isinstance(value, list):
        return []
    normalized = " ".join(re.sub(r"[`*_~]", "", text).casefold().split())
    covered = bytearray(len(normalized))
    coordinates = []
    for item in value:
        minimum_length = 2 if field == "product.formats" else 4
        if not isinstance(item, str) or len(item.strip()) < minimum_length:
            continue
        phrase = " ".join(item.casefold().split())
        starts = []
        cursor = 0
        while (start := normalized.find(phrase, cursor)) >= 0:
            starts.append(start)
            cursor = start + len(phrase)
        if not starts:
            continue
        for start in starts:
            covered[start : start + len(phrase)] = b"\x01" * len(phrase)
        coordinates.append(
            _coordinate(
                fact_id=fact_id,
                field=field,
                path=f"/items/{_canonical_sha256(item)[:16]}",
                value=item,
            )
        )
    remainder = "".join(
        character for index, character in enumerate(normalized) if not covered[index]
    )
    return coordinates if not re.sub(r"[^a-z0-9]+", "", remainder) else []


def literal_list_fact_coordinates(
    text: str,
    fact_id: str,
    field: str,
    value: object,
) -> list[StructuredFactCoordinateV1]:
    """Return exact list-item coordinates visibly present in a compound claim."""

    if not isinstance(value, list):
        return []
    normalized = " ".join(re.sub(r"[`*_~]", "", text).casefold().split())
    coordinates = []
    for item in value:
        minimum_length = 2 if field == "product.formats" else 4
        if not isinstance(item, str) or len(item.strip()) < minimum_length:
            continue
        visible_item = (
            re.sub(r"(?i)^(?:input|output)\s+format\s*:\s*", "", item).strip()
            if field == "product.formats"
            else item
        )
        item_visible = " ".join(visible_item.casefold().split()) in normalized
        if field == "product.formats":
            role_match = re.match(r"(?i)^(input|output)\s+format\s*:", item)
            if role_match is not None:
                item_visible = bool(
                    item_visible
                    and _format_role_is_explicit(
                        text,
                        visible_item,
                        role_match.group(1).casefold(),
                    )
                )
        if item_visible:
            coordinates.append(structured_list_item_coordinate(fact_id, field, item))
    return coordinates


def structured_list_item_coordinate(
    fact_id: str,
    field: str,
    value: str,
) -> StructuredFactCoordinateV1:
    """Return the canonical coordinate for one exact selected-list value."""

    return _coordinate(
        fact_id=fact_id,
        field=field,
        path=f"/items/{_canonical_sha256(value)[:16]}",
        value=value,
    )


def _input_fixture_coordinates(
    text: str,
    fact_id: str,
    value: object,
) -> list[StructuredFactCoordinateV1]:
    if not isinstance(value, dict) or not isinstance(value.get("input_fixture_bindings"), list):
        return []
    match = _VERIFIED_INPUT.fullmatch(text)
    if match is None:
        return []
    matches = {(match.group("target"), match.group("source"))}
    coordinates = []
    for binding in value["input_fixture_bindings"]:
        if not isinstance(binding, dict):
            continue
        pair = (binding.get("target_path"), binding.get("source_path"))
        if pair not in matches:
            continue
        coordinates.append(
            _coordinate(
                fact_id=fact_id,
                field="example.minimal",
                path=f"/input_fixture_bindings/{_canonical_sha256(pair)[:16]}",
                value=binding,
            )
        )
    return coordinates


def _verified_acquisition_coordinates(
    text: str,
    facts: ProductFactsV2,
    fact_id: str,
    value: object,
    source_revision: str | None,
) -> list[StructuredFactCoordinateV1]:
    if not isinstance(value, dict) or not source_revision:
        return []
    expected = installation_text(facts, facts.org_repo, source_revision)
    if expected is None or text.strip() not in _material_claim_texts(expected):
        return []
    return [
        _coordinate(
            fact_id=fact_id,
            field="installation.verified_acquisition",
            path="/verified-rendered-acquisition",
            value=value,
        )
    ]


def structured_fact_coordinates(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    facts: ProductFactsV2,
    fact_ids: Iterable[str] | None = None,
) -> list[StructuredFactCoordinateV1]:
    """Return exact typed coordinates expressed by one constrained claim shape."""

    selected = sorted(set(fact_ids or facts.selected_fact_ids.values()))
    text = _document_bytes(document)[claim.source_byte_start : claim.source_byte_end].decode(
        "utf-8"
    )
    context = _claim_context(document, claim)
    coordinates: list[StructuredFactCoordinateV1] = []
    for fact_id in selected:
        fact = facts.fact_by_id(fact_id)
        if facts.selected_fact_ids.get(fact.field) != fact_id:
            continue
        if fact.verification_state not in {"verified", "policy_approved"}:
            continue
        if fact.has_unresolved_conflict:
            continue
        if fact.field == "api.public_surface":
            coordinates.extend(api_structured_fact_coordinates(text, context, fact_id, fact.value))
        elif fact.field == "development.golden_workflow":
            coordinates.extend(golden_workflow_fact_coordinates(text, fact_id, fact.value))
        elif fact.field == "installation.optional_extras":
            coordinates.extend(_optional_extra_coordinates(text, facts, fact_id, fact.value))
        elif fact.field == "installation.coordinates":
            coordinates.extend(
                python_source_build_distribution_coordinates(
                    text,
                    facts,
                    fact_id,
                    fact.value,
                    fact.source.source_revision,
                )
            )
        elif fact.field in {
            "product.capabilities",
            "product.formats",
            "product.problems_solved",
        }:
            coordinates.extend(_exact_list_coordinates(text, fact_id, fact.field, fact.value))
        elif fact.field == "product.limitations":
            coordinates.extend(public_limitation_fact_coordinates(text, fact_id, facts))
        elif fact.field == "example.minimal":
            coordinates.extend(_input_fixture_coordinates(text, fact_id, fact.value))
        elif fact.field == "installation.verified_acquisition":
            coordinates.extend(
                _verified_acquisition_coordinates(
                    text,
                    facts,
                    fact_id,
                    fact.value,
                    fact.source.source_revision,
                )
            )
    return sorted(
        set(coordinates),
        key=lambda item: (item.fact_id, item.path, item.value_sha256),
    )
