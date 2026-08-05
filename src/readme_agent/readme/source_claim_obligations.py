"""Define fact and provenance contracts for inherited README obligations."""

from __future__ import annotations

from typing import Literal

from readme_agent.facts.schema_v2 import ProductFactsV2

SourceClaimObligation = Literal[
    "product_overview",
    "major_capabilities",
    "verified_installation",
    "primary_example",
    "scope_and_limitations",
    "third_party_notices",
    "license",
    "contextual_product_relationship",
    "compatibility",
]

_OBLIGATION_FACT_FIELDS: dict[SourceClaimObligation, frozenset[str]] = {
    "product_overview": frozenset({"product.identity"}),
    "major_capabilities": frozenset({"product.capabilities"}),
    "verified_installation": frozenset(
        {"installation.verified_acquisition", "installation.coordinates"}
    ),
    "primary_example": frozenset({"example.minimal"}),
    "scope_and_limitations": frozenset({"product.limitations"}),
    "third_party_notices": frozenset({"repository.third_party_notices"}),
    "license": frozenset({"product.license"}),
    "contextual_product_relationship": frozenset({"relationship.commercial_foss"}),
    "compatibility": frozenset({"product.compatibility"}),
}
_OBLIGATION_ANY_FACT_FIELDS: dict[SourceClaimObligation, frozenset[str]] = {
    "product_overview": frozenset(
        {"product.audience", "product.problems_solved", "product.capabilities"}
    )
}
_OBLIGATION_PROVENANCE_PREFIXES: dict[SourceClaimObligation, tuple[str, ...]] = {
    "product_overview": ("template.title", "template.summary"),
    "major_capabilities": ("template.section.key_capabilities",),
    "verified_installation": ("template.section.installation",),
    "primary_example": ("template.section.quick_start",),
    "scope_and_limitations": ("template.section.scope_and_limitations",),
    "third_party_notices": ("template.section.third_party_notices",),
    "license": ("template.section.license",),
    "contextual_product_relationship": ("template.section.scope_and_limitations",),
    "compatibility": ("template.section.installation",),
}
_OVERVIEW_FACT_FIELDS = (
    "product.identity",
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
    "product.license",
)
_SOURCE_ENTAILMENT_REQUIRED = frozenset({"primary_example", "compatibility"})


def applicable_product_overview_fact_ids(facts: ProductFactsV2) -> set[str]:
    """Return the complete selected accepted fact family for an overview replacement."""

    result: set[str] = set()
    for field in _OVERVIEW_FACT_FIELDS:
        fact_id = facts.selected_fact_ids.get(field)
        if fact_id is None:
            continue
        fact = facts.fact_by_id(fact_id)
        if (
            fact.verification_state in {"verified", "policy_approved"}
            and not fact.has_unresolved_conflict
        ):
            result.add(fact_id)
    return result


def obligation_required_fact_fields(obligation: SourceClaimObligation) -> frozenset[str]:
    """Return fact fields every replacement for this obligation must cite."""

    return _OBLIGATION_FACT_FIELDS[obligation]


def obligation_any_fact_fields(obligation: SourceClaimObligation) -> frozenset[str]:
    """Return a field group from which at least one citation is required."""

    return _OBLIGATION_ANY_FACT_FIELDS.get(obligation, frozenset())


def obligation_provenance_prefixes(obligation: SourceClaimObligation) -> tuple[str, ...]:
    """Return exact golden-slot prefixes allowed to replace this obligation."""

    return _OBLIGATION_PROVENANCE_PREFIXES[obligation]


def obligation_requires_source_entailment(obligation: SourceClaimObligation) -> bool:
    """Return whether a replacement must semantically entail the complete source claim."""

    return obligation in _SOURCE_ENTAILMENT_REQUIRED
