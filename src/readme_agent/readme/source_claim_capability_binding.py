"""Bind feature-section details to structured capability, format, and API evidence."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.claim_accountability_api_index import api_coordinate_index
from readme_agent.readme.claim_accountability_api_shapes import coded_references
from readme_agent.readme.source_claim_api_detail_binding import (
    technical_references_are_known,
)
from readme_agent.readme.source_claim_context import descendant_list_text, heading_ancestry

_CAMEL_WORD = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z]?[a-z]+|[0-9]+")
_FORMAT_TOKEN = re.compile(
    r"(?:(?i:(?<![a-z0-9])\.[a-z0-9]+)|\b[A-Z][A-Z0-9]{1,}\b|\b[0-9][A-Z0-9]{2,}\b)"
)
_STOP_WORDS = frozenset(
    {"and", "aspose", "content", "from", "nodes", "only", "the", "to", "via", "with"}
)
_FEATURE_DETAIL_WORDS = frozenset(
    {
        "based",
        "binary",
        "byte",
        "dimension",
        "dom",
        "extraction",
        "file",
        "hyperlink",
        "lab",
        "like",
        "nested",
        "path",
        "read",
        "report",
        "search",
        "stream",
        "tagged",
        "type",
        "use",
        "uses",
    }
)


def _accepted_fact(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


def _anchor_words(value: str) -> frozenset[str]:
    expanded = " ".join(_CAMEL_WORD.findall(re.sub(r"[`*_~]", "", value)))
    return frozenset(
        "number" if token == "numbered" else token.removesuffix("s")
        for token in re.findall(r"[a-z0-9]+", expanded.casefold())
        if len(token) >= 3 and token not in _STOP_WORDS
    )


def _api_class_mentions(text: str, value: dict, *, exact_spelling: bool) -> frozenset[str]:
    mentions = set()
    for name in api_coordinate_index(value).classes_by_name:
        expanded = " ".join(_CAMEL_WORD.findall(name))
        patterns = (name, expanded)
        flags = 0 if exact_spelling else re.IGNORECASE
        if any(re.search(rf"\b{re.escape(pattern)}(?:s)?\b", text, flags) for pattern in patterns):
            mentions.add(name)
    return frozenset(mentions)


def _matching_capabilities(text: str, value: object, api_value: dict | None) -> list[str]:
    if not isinstance(value, list):
        return []
    claim_words = _anchor_words(text)
    claim_api_mentions = (
        _api_class_mentions(text, api_value, exact_spelling=False)
        if api_value is not None
        else set()
    )
    claim_api_words = frozenset(word for name in claim_api_mentions for word in _anchor_words(name))
    matches = []
    for item in value:
        if not isinstance(item, str):
            continue
        anchors = _anchor_words(item)
        required = anchors - {"document", "format", "page"} or anchors
        item_api_mentions = (
            _api_class_mentions(item, api_value, exact_spelling=True)
            if api_value is not None
            else set()
        )
        exact_api_anchor = item_api_mentions & claim_api_mentions
        exact_structured_text = required <= claim_words and claim_words <= anchors
        supported_detail = (
            required <= claim_words
            and (claim_words - anchors - claim_api_words) <= _FEATURE_DETAIL_WORDS
        )
        if required and (exact_structured_text or exact_api_anchor or supported_detail):
            matches.append(item)
    return matches


def _format_tokens(value: str) -> frozenset[str]:
    return frozenset(match.group(0).casefold() for match in _FORMAT_TOKEN.finditer(value))


def _matching_formats(text: str, value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    claim_tokens = _format_tokens(text)
    return [
        item
        for item in value
        if isinstance(item, str)
        and (tokens := _format_tokens(item))
        and bool(tokens & claim_tokens)
    ]


def _dependency_names(text: str, value: object) -> frozenset[str]:
    if not isinstance(value, dict) or not isinstance(value.get("entries"), list):
        return frozenset()
    folded = text.casefold()
    return frozenset(
        name
        for entry in value["entries"]
        if isinstance(entry, dict)
        for name in (str(entry.get("distribution") or "").casefold(),)
        if name and re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", folded)
    )


def _api_references_are_known(
    text: str,
    api_value: dict,
    accepted_format_tokens: frozenset[str],
) -> tuple[bool, bool]:
    has_api_reference = False
    for reference, _tail in coded_references(text):
        if reference.casefold() in accepted_format_tokens:
            continue
        valid, _owners = technical_references_are_known(
            f"- `{reference}`",
            (),
            api_value,
        )
        if not valid:
            return False, False
        has_api_reference = True
    return True, has_api_reference


def feature_detail_fact_ids(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    text: str,
    facts: ProductFactsV2,
) -> set[str]:
    """Bind one feature detail without semantic similarity or product-specific exceptions."""

    headings = " ".join(heading_ancestry(document, claim)).casefold()
    if "feature" not in headings and "capabilit" not in headings:
        return set()
    capabilities = _accepted_fact(facts, "product.capabilities")
    formats = _accepted_fact(facts, "product.formats")
    api = _accepted_fact(facts, "api.public_surface")
    api_value = api.value if api is not None and isinstance(api.value, dict) else None
    combined = f"{text} {descendant_list_text(document, claim)}"
    capability_matches = (
        _matching_capabilities(combined, capabilities.value, api_value) if capabilities else []
    )
    format_matches = _matching_formats(combined, formats.value) if formats else []
    result: set[str] = set()
    if capability_matches and capabilities is not None:
        result.add(capabilities.fact_id)
    if format_matches and formats is not None:
        result.add(formats.fact_id)
    if not result:
        return set()

    if api_value is not None and api is not None:
        accepted_format_tokens = frozenset(
            token for item in format_matches for token in _format_tokens(item)
        )
        valid, has_api_reference = _api_references_are_known(
            text,
            api_value,
            accepted_format_tokens,
        )
        if not valid:
            return set()
        plain_api_names = {
            name
            for name in api_coordinate_index(api_value).classes_by_name
            if re.search(rf"\b{re.escape(name)}\b", combined)
        }
        if has_api_reference or plain_api_names:
            result.add(api.fact_id)

    dependencies = _accepted_fact(facts, "installation.capability_dependencies")
    if dependencies is not None and _dependency_names(text, dependencies.value):
        result.add(dependencies.fact_id)
    return result


__all__ = ["feature_detail_fact_ids"]
