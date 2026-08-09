"""Bind repository-authored API details to exact structured public-surface evidence."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.claim_accountability_api_index import api_coordinate_index
from readme_agent.readme.claim_accountability_api_shapes import (
    coded_references,
    compatible_member_reference,
    member_surfaces,
)
from readme_agent.readme.source_claim_context import heading_ancestry, list_ancestor_bodies

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_API_DETAIL_WORDS = frozenset(
    """a abstract across base below best by change compatibility container contents default
    detail effort encryption entry everything field for formatted formatting has historical image
    implementation indexing internal is iteration level may nodes not only over paragraph password
    points property public recursive replace revisions root search segments stub subset supported
    surface text the those to traversal type under up used visitor walk""".split()
)


def _accepted_fact(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


def _reference_class_name(reference: str, value: dict) -> str | None:
    index = api_coordinate_index(value)
    raw = reference.strip()
    if raw in index.classes_by_name:
        return raw
    first = raw.split("(", 1)[0].split(":", 1)[0].split(" -> ", 1)[0].strip()
    if first in index.classes_by_name:
        return first
    if "." in first:
        module_name, _, name = first.rpartition(".")
        if name in index.classes_by_name and any(
            str(module.get("module")) == module_name
            for module in index.modules_by_export.get(name, ())
        ):
            return name
    return None


def _context_class_names(ancestors: tuple[str, ...], value: dict) -> list[str]:
    index = api_coordinate_index(value)
    names: list[str] = []
    for ancestor in ancestors:
        for reference, _tail in coded_references(ancestor):
            class_name = _reference_class_name(reference, value)
            if class_name and class_name not in names:
                names.append(class_name)
        for token in _IDENTIFIER.findall(ancestor):
            if token in index.classes_by_name and token not in names:
                names.append(token)
    return names


def _constructor_parameter_names(class_item: dict) -> frozenset[str]:
    constructor = class_item.get("constructor")
    if not isinstance(constructor, dict) or not isinstance(constructor.get("parameters"), list):
        return frozenset()
    return frozenset(
        str(parameter["name"])
        for parameter in constructor["parameters"]
        if isinstance(parameter, dict) and isinstance(parameter.get("name"), str)
    )


def _context_member_matches(reference: str, class_item: dict) -> bool:
    member_name = reference.split("(", 1)[0].split(":", 1)[0].split(" -> ", 1)[0].strip()
    members = [
        member
        for member in class_item.get("members", [])
        if isinstance(member, dict) and member.get("name") == member_name
    ]
    if members and (
        compatible_member_reference(reference, member_surfaces(members))
        or any(member.get("name") == member_name for member in members)
    ):
        return True
    return member_name in _constructor_parameter_names(class_item)


def _api_reference_known(reference: str, context_names: list[str], value: dict) -> bool:
    index = api_coordinate_index(value)
    normalized = reference.strip()
    if re.fullmatch(r"for\s+[a-z_][a-z0-9_]*\s+in\s+[a-z_][a-z0-9_]*:\s*\.\.\.", normalized):
        return any(
            any(
                member.get("name") == "GetEnumerator"
                for member in index.classes_by_name[name].get("members", [])
            )
            for name in context_names
        )
    if normalized in index.modules_by_name:
        return True
    class_name = _reference_class_name(normalized, value)
    if class_name is not None:
        unknown_types = {
            token
            for token in _IDENTIFIER.findall(normalized)[1:]
            if token[:1].isupper()
            and token not in index.classes_by_name
            and token not in {"Any", "BinaryIO", "None", "Path", "Type"}
        }
        return not unknown_types
    if "." in normalized:
        owner, _, member_reference = normalized.partition(".")
        if owner in index.classes_by_name:
            nested = member_reference.split(".")
            if not _context_member_matches(nested[0], index.classes_by_name[owner]):
                return False
            return all(
                token in index.classes_by_name
                or any(
                    member.get("name") == token
                    for item in index.classes_by_name.values()
                    for member in item.get("members", [])
                )
                for token in _IDENTIFIER.findall(".".join(nested[1:]))
                if token[:1].isupper()
            )
    return any(
        _context_member_matches(normalized, index.classes_by_name[name]) for name in context_names
    )


def technical_references_are_known(
    text: str,
    ancestors: tuple[str, ...],
    value: dict,
) -> tuple[bool, frozenset[str]]:
    """Validate every code reference and return its exact API class owners."""

    references = coded_references(text)
    context_names = _context_class_names(ancestors, value)
    mentioned_classes = [
        class_name
        for reference, _tail in references
        if (class_name := _reference_class_name(reference, value)) is not None
    ]
    active_context = list(dict.fromkeys([*context_names, *mentioned_classes]))
    return (
        all(_api_reference_known(reference, active_context, value) for reference, _ in references),
        frozenset(mentioned_classes),
    )


def _api_residual_words(text: str) -> frozenset[str]:
    residual = re.sub(r"`[^`]+`", " ", text)
    residual = re.sub(r"[*_~#✅]", " ", residual)
    return frozenset(re.findall(r"[a-z]+", residual.casefold()))


def _qualifiers_are_supported(
    text: str,
    context_names: list[str],
    value: dict,
    facts: ProductFactsV2,
) -> set[str] | None:
    words = _api_residual_words(text)
    if not words <= _API_DETAIL_WORDS:
        return None
    index = api_coordinate_index(value)
    context_members = {
        str(member.get("name"))
        for name in context_names
        for member in index.classes_by_name[name].get("members", [])
        if isinstance(member, dict)
    }
    if {"iteration", "indexing"} & words and "GetEnumerator" not in context_members:
        return None
    if "recursive" in words and "GetChildNodes" not in text:
        return None
    if "replace" in words and "Replace" not in text:
        return None
    if "property" in words and not any(
        member.get("kind") == "property" and str(member.get("name")) in text
        for name in context_names
        for member in index.classes_by_name[name].get("members", [])
        if isinstance(member, dict)
    ):
        return None
    if re.search(r"\(\s*base\s*\)", text, re.IGNORECASE) and not any(
        name in item.get("bases", [])
        for name in context_names
        for item in index.classes_by_name.values()
        if isinstance(item.get("bases"), list)
    ):
        return None
    result: set[str] = set()
    if "not" in words and "supported" in words:
        limitation = _accepted_fact(facts, "product.limitations")
        technical = {token.casefold() for token in _IDENTIFIER.findall(text) if token[:1].isupper()}
        if (
            limitation is None
            or not isinstance(limitation.value, list)
            or not any(
                technical and any(token in str(item).casefold() for token in technical)
                for item in limitation.value
            )
        ):
            return None
        result.add(limitation.fact_id)
    return result


def api_detail_fact_ids(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    text: str,
    facts: ProductFactsV2,
) -> set[str]:
    """Bind one API-section detail only when identifiers and qualifiers are constrained."""

    if "api" not in " ".join(heading_ancestry(document, claim)).casefold():
        return set()
    api = _accepted_fact(facts, "api.public_surface")
    if api is None or not isinstance(api.value, dict):
        return set()
    folded = " ".join(text.casefold().split())
    references = coded_references(text)
    namespaces = {
        str(item) for item in api.value.get("package_namespaces", []) if isinstance(item, str)
    }
    if not text.lstrip().startswith(("-", "+", "*")):
        mentioned = {reference for reference, _tail in references}
        if folded.startswith("the supported public entry points are "):
            internal = {name for name in mentioned if name.endswith("._internal")}
            public = mentioned - internal
            if public != namespaces or any(
                name.removesuffix("._internal") not in namespaces for name in internal
            ):
                return set()
            return {api.fact_id}
        if folded == "below is the supported public surface across those entry points.":
            return {api.fact_id}
        return set()

    ancestors = list_ancestor_bodies(document, claim)
    context_names = _context_class_names(ancestors, api.value)
    valid, mentioned_classes = technical_references_are_known(text, ancestors, api.value)
    if not valid:
        return set()
    if not references:
        words = _api_residual_words(text)
        if {"iteration", "indexing"} & words:
            pass
        elif "abstract compatibility base type" in folded:
            if not context_names or not any(
                name in item.get("bases", [])
                for name in context_names
                for item in api_coordinate_index(api.value).classes_by_name.values()
                if isinstance(item.get("bases"), list)
            ):
                return set()
        else:
            return set()
    active_context = list(dict.fromkeys([*context_names, *mentioned_classes]))
    qualifier_ids = _qualifiers_are_supported(text, active_context, api.value, facts)
    return set() if qualifier_ids is None else {api.fact_id, *qualifier_ids}


__all__ = ["api_detail_fact_ids", "technical_references_are_known"]
