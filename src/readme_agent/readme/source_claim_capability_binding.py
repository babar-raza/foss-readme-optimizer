"""Bind feature-section details to structured capability, format, and API evidence."""

from __future__ import annotations

import re
from functools import lru_cache

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.claim_accountability_api_index import api_coordinate_index
from readme_agent.readme.claim_accountability_api_shapes import coded_references
from readme_agent.readme.claim_accountability_implementation_coordinates import (
    implementation_component_coordinates,
)
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
_API_DETAIL_SYNONYMS = {
    "arrow": frozenset({"arrowhead"}),
    "byte": frozenset({"binary"}),
    "create": frozenset({"add", "insert", "new"}),
    "embed": frozenset({"add", "insert", "replace"}),
    "iterate": frozenset({"array", "enumerable"}),
    "threaded": frozenset({"parent"}),
    "thread": frozenset({"parent"}),
    "timestamp": frozenset({"created", "date", "time"}),
}
_FEATURE_SEPARATOR = re.compile(r"\s+(?:—|–|-)\s+")


def _accepted_fact(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


def _anchor_words(value: str) -> frozenset[str]:
    expanded = " ".join(_CAMEL_WORD.findall(re.sub(r"[`*~]", "", value).replace("_", " ")))
    return frozenset(
        "number" if token == "numbered" else token.removesuffix("s")
        for token in re.findall(r"[a-z0-9]+", expanded.casefold())
        if len(token) >= 3 and token not in _STOP_WORDS
    )


@lru_cache(maxsize=16)
def _api_class_mention_index(
    class_names: tuple[str, ...],
    exact_spelling: bool,
) -> tuple[re.Pattern[str] | None, dict[str, frozenset[str]]]:
    phrases: dict[str, set[str]] = {}
    for name in class_names:
        expanded = " ".join(_CAMEL_WORD.findall(name))
        for phrase in {name, expanded} - {""}:
            key = phrase if exact_spelling else phrase.casefold()
            phrases.setdefault(key, set()).add(name)
    if not phrases:
        return None, {}
    alternatives = "|".join(re.escape(phrase) for phrase in sorted(phrases, key=len, reverse=True))
    flags = 0 if exact_spelling else re.IGNORECASE
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_])(?P<name>{alternatives})(?:s)?(?![A-Za-z0-9_])",
        flags,
    )
    return pattern, {key: frozenset(names) for key, names in phrases.items()}


def _api_class_mentions(text: str, value: dict, *, exact_spelling: bool) -> frozenset[str]:
    class_names = tuple(api_coordinate_index(value).classes_by_name)
    pattern, phrases = _api_class_mention_index(class_names, exact_spelling)
    if pattern is None:
        return frozenset()
    mentions: set[str] = set()
    for match in pattern.finditer(text):
        key = match.group("name") if exact_spelling else match.group("name").casefold()
        mentions.update(phrases[key])
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


def _public_api_feature_evidence(
    text: str,
    api_value: dict,
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Return relevant API types, material detail terms, and supported detail terms."""

    visible = re.sub(r"[`*_~]", "", text.splitlines()[0]).strip().lstrip("-+ ")
    parts = _FEATURE_SEPARATOR.split(visible, maxsplit=1)
    if len(parts) != 2:
        return frozenset(), frozenset(), frozenset()
    label, detail = parts
    label_words = _anchor_words(label)
    if not label_words:
        return frozenset(), frozenset(), frozenset()
    index = api_coordinate_index(api_value)
    relevant = frozenset(
        name for name in index.classes_by_name if label_words.intersection(_anchor_words(name))
    )
    if not relevant:
        return frozenset(), frozenset(), frozenset()
    member_words = frozenset(
        word
        for name in relevant
        for member in index.classes_by_name[name].get("members", [])
        if isinstance(member, dict) and isinstance(member.get("name"), str)
        for word in _anchor_words(member["name"])
    )
    detail_words = _anchor_words(detail) - label_words
    supported = frozenset(
        word
        for word in detail_words
        if word in member_words or bool(_API_DETAIL_SYNONYMS.get(word, frozenset()) & member_words)
    )
    return relevant, detail_words, supported


def public_api_feature_is_anchored(text: str, facts: ProductFactsV2) -> bool:
    """Return whether an inherited feature is narrowly related to accepted public API evidence."""

    api = _accepted_fact(facts, "api.public_surface")
    if api is None or not isinstance(api.value, dict):
        return False
    relevant, detail_words, supported = _public_api_feature_evidence(text, api.value)
    return bool(relevant and len(detail_words) >= 3 and supported)


def public_api_feature_is_entailed(text: str, facts: ProductFactsV2) -> bool:
    """Accept only a multi-anchor feature whose every material detail has API support."""

    api = _accepted_fact(facts, "api.public_surface")
    if api is None or not isinstance(api.value, dict):
        return False
    relevant, detail_words, supported = _public_api_feature_evidence(text, api.value)
    return bool(relevant and len(detail_words) >= 3 and detail_words == supported)


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
    plain_api_mentions = (
        _api_class_mentions(combined, api_value, exact_spelling=False)
        if api_value is not None
        else frozenset()
    )
    distinctive_api_mentions = {
        name for name in plain_api_mentions if name.isupper() or len(_anchor_words(name)) >= 2
    }
    if len(plain_api_mentions) >= 2:
        distinctive_api_mentions.update(plain_api_mentions)
    if distinctive_api_mentions and api is not None:
        result.add(api.fact_id)
    if api is not None and public_api_feature_is_entailed(text, facts):
        result.add(api.fact_id)
    implementation = _accepted_fact(facts, "repository.implementation_components")
    known_api_names: set[str] = set()
    if api_value is not None:
        api_index = api_coordinate_index(api_value)
        known_api_names.update(api_index.classes_by_name)
        known_api_names.update(api_index.all_member_names)
        known_api_names.update(api_index.modules_by_export)
        known_api_names.update(api_index.package_export_names)
    if implementation is not None and implementation_component_coordinates(
        combined,
        implementation.fact_id,
        implementation.value,
        known_non_dependency_names=known_api_names,
    ):
        result.add(implementation.fact_id)
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


__all__ = [
    "feature_detail_fact_ids",
    "public_api_feature_is_anchored",
    "public_api_feature_is_entailed",
]
