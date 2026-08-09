"""Bind exact structured capability and API claims to canonical coordinates."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.claim_accountability_api_coordinates import (
    api_class_fact_coordinates,
    api_structured_fact_coordinates,
)
from readme_agent.readme.claim_accountability_api_index import api_coordinate_index
from readme_agent.readme.claim_accountability_api_shapes import (
    coded_references,
    compatible_member_reference,
    context_classes,
    has_only_api_punctuation,
    member_surfaces,
)
from readme_agent.readme.claim_accountability_coordinates import (
    structured_list_item_coordinate,
)
from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1
from readme_agent.readme.source_claim_context import list_ancestor_bodies

_LIST_ITEM = re.compile(r"(?s)^(?P<indent>[ \t]*)[-+*]\s+(?P<body>.+?)\s*$")


def _accepted_fact(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


def _api_coordinates(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    text: str,
    fact: FactRecordV2,
) -> list[StructuredFactCoordinateV1]:
    item = _LIST_ITEM.fullmatch(text.strip())
    if item is None:
        return []
    ancestors = list_ancestor_bodies(document, claim)
    context = ancestors[-1] if ancestors else ""
    coordinates = api_structured_fact_coordinates(
        text,
        context,
        fact.fact_id,
        fact.value,
    )
    if coordinates or not context:
        return coordinates
    coordinates = api_structured_fact_coordinates(
        f"- {context} — {item.group('body')}",
        "",
        fact.fact_id,
        fact.value,
    )
    return coordinates or _nested_api_union_coordinates(context, item.group("body"), fact)


def _nested_api_union_coordinates(
    context: str,
    body: str,
    fact: FactRecordV2,
) -> list[StructuredFactCoordinateV1]:
    if not isinstance(fact.value, dict) or not has_only_api_punctuation(body):
        return []
    index = api_coordinate_index(fact.value)
    class_names = context_classes(context, index.classes_by_name)
    references = coded_references(body)
    if not class_names or not references:
        return []
    coordinates = api_class_fact_coordinates(fact.fact_id, fact.value, class_names)
    if not coordinates:
        return []
    for reference, _tail in references:
        if reference in index.classes_by_name:
            reference_coordinates = api_class_fact_coordinates(
                fact.fact_id,
                fact.value,
                [reference],
            )
        else:
            member_name = reference.split("(", 1)[0].split(":", 1)[0].strip()
            owners = [
                class_name
                for class_name in class_names
                if compatible_member_reference(
                    reference,
                    member_surfaces(
                        [
                            member
                            for member in index.classes_by_name[class_name].get("members", [])
                            if member.get("name") == member_name
                        ]
                    ),
                )
            ]
            reference_coordinates = [
                coordinate
                for class_name in owners
                for coordinate in api_structured_fact_coordinates(
                    f"- `{class_name}` — `{reference}`",
                    "",
                    fact.fact_id,
                    fact.value,
                )
            ]
        if not reference_coordinates:
            return []
        coordinates.extend(reference_coordinates)
    return sorted(set(coordinates), key=lambda item: (item.path, item.value_sha256))


def _visible_text(value: str) -> str:
    return " ".join(re.sub(r"[`*_~]", "", value).casefold().split())


def exact_structured_fact_ids(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    text: str,
    facts: ProductFactsV2,
) -> set[str]:
    """Return exact capability/API fact IDs after canonical coordinate validation."""

    api = _accepted_fact(facts, "api.public_surface")
    api_coordinates = (
        _api_coordinates(document, claim, text, api)
        if api is not None and isinstance(api.value, dict)
        else []
    )
    api_ids = {coordinate.fact_id for coordinate in api_coordinates}

    item = _LIST_ITEM.fullmatch(text.strip())
    capability = _accepted_fact(facts, "product.capabilities")
    if item is None or capability is None or not isinstance(capability.value, list):
        return api_ids
    body = item.group("body")
    visible_body = _visible_text(body)
    matches = [
        value
        for value in capability.value
        if isinstance(value, str) and visible_body and _visible_text(value) == visible_body
    ]
    if len(matches) != 1:
        return api_ids
    capability_coordinate = structured_list_item_coordinate(
        capability.fact_id,
        capability.field,
        matches[0],
    )
    if coded_references(body) and not api_coordinates:
        return api_ids
    return {capability_coordinate.fact_id, *api_ids}


__all__ = ["exact_structured_fact_ids"]
