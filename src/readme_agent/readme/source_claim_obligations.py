"""Define fact and provenance contracts for inherited README obligations."""

from __future__ import annotations

from typing import Literal

from readme_agent.facts.schema_v2 import ProductFactsV2

SourceClaimObligation = Literal[
    "header_badges",
    "product_overview",
    "navigation",
    "at_a_glance",
    "major_capabilities",
    "verified_installation",
    "dependency_requirements",
    "primary_example",
    "additional_examples",
    "api_public_surface",
    "api_structure",
    "documentation_resources",
    "support_routes",
    "scope_and_limitations",
    "development_commands",
    "golden_workflow",
    "repository_map",
    "contribution_guidance",
    "security_guidance",
    "third_party_notices",
    "license",
    "contextual_product_relationship",
    "compatibility",
]

_OBLIGATION_FACT_FIELDS: dict[SourceClaimObligation, frozenset[str]] = {
    "header_badges": frozenset({"product.identity", "product.license"}),
    "product_overview": frozenset({"product.identity"}),
    "navigation": frozenset(),
    "at_a_glance": frozenset({"product.capabilities", "product.formats"}),
    "major_capabilities": frozenset({"product.capabilities"}),
    "verified_installation": frozenset(
        {"installation.verified_acquisition", "installation.coordinates"}
    ),
    "dependency_requirements": frozenset(),
    "primary_example": frozenset({"example.minimal"}),
    "additional_examples": frozenset({"repository.examples"}),
    "api_public_surface": frozenset({"api.public_surface"}),
    "api_structure": frozenset(),
    "documentation_resources": frozenset({"documentation.links"}),
    "support_routes": frozenset({"support.routes"}),
    "scope_and_limitations": frozenset({"product.limitations"}),
    "development_commands": frozenset({"development.commands"}),
    "golden_workflow": frozenset({"development.golden_workflow"}),
    "repository_map": frozenset(),
    "contribution_guidance": frozenset({"repository.contribution_guidance"}),
    "security_guidance": frozenset({"repository.security_guidance"}),
    "third_party_notices": frozenset({"repository.third_party_notices"}),
    "license": frozenset({"product.license"}),
    "contextual_product_relationship": frozenset({"relationship.commercial_foss"}),
    "compatibility": frozenset({"product.compatibility"}),
}
_OBLIGATION_ANY_FACT_FIELDS: dict[SourceClaimObligation, frozenset[str]] = {
    "header_badges": frozenset(
        {"installation.coordinates", "product.compatibility", "release.state"}
    ),
    "product_overview": frozenset(
        {"product.audience", "product.problems_solved", "product.capabilities"}
    ),
    "dependency_requirements": frozenset(
        {
            "installation.capability_dependencies",
            "installation.optional_extras",
            "python.distribution",
        }
    ),
    "repository_map": frozenset(
        {
            "api.public_surface",
            "development.assets",
            "development.commands",
            "repository.ci",
            "repository.documentation_assets",
        }
    ),
}
_OBLIGATION_PROVENANCE_PREFIXES: dict[SourceClaimObligation, tuple[str, ...]] = {
    "header_badges": ("template.badges",),
    "product_overview": ("template.title", "template.summary"),
    "navigation": ("template.navigation",),
    "at_a_glance": ("template.section.at_a_glance",),
    "major_capabilities": ("template.section.key_capabilities",),
    "verified_installation": ("template.section.installation",),
    "dependency_requirements": ("template.section.installation",),
    "primary_example": ("template.section.quick_start",),
    "additional_examples": ("template.section.additional_examples",),
    "api_public_surface": (
        "template.section.api_reference",
        "template.section.additional_examples",
        "template.section.installation",
    ),
    "api_structure": ("template.section.api_reference",),
    "documentation_resources": ("template.section.documentation_resources",),
    "support_routes": ("template.section.documentation_resources",),
    "scope_and_limitations": ("template.section.scope_and_limitations",),
    "development_commands": ("template.section.development_and_testing",),
    "golden_workflow": ("template.section.development_and_testing",),
    "repository_map": ("template.section.development_and_testing",),
    "contribution_guidance": ("template.section.contributing",),
    "security_guidance": ("template.section.security",),
    "third_party_notices": ("template.section.third_party_notices",),
    "license": ("template.section.license",),
    "contextual_product_relationship": ("template.section.scope_and_limitations",),
    "compatibility": ("template.section.installation", "template.badges"),
}
_OBLIGATION_STANDARD_IDS: dict[SourceClaimObligation, frozenset[str]] = {
    "header_badges": frozenset({"readme.badges"}),
    "navigation": frozenset({"readme.navigation"}),
    "at_a_glance": frozenset({"readme.at_a_glance_mermaid"}),
    "api_structure": frozenset({"readme.api_reference"}),
}
_OVERVIEW_FACT_FIELDS = (
    "product.identity",
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
    "product.license",
)
_SOURCE_ENTAILMENT_REQUIRED = frozenset(
    {
        "api_public_surface",
        "contribution_guidance",
        "dependency_requirements",
        "golden_workflow",
        "major_capabilities",
        "primary_example",
        "product_overview",
        "repository_map",
        "security_guidance",
    }
)


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


def obligation_required_standard_ids(obligation: SourceClaimObligation) -> frozenset[str]:
    """Return configured standards required on the matching candidate slot."""

    return _OBLIGATION_STANDARD_IDS.get(obligation, frozenset())


def obligation_requires_source_entailment(obligation: SourceClaimObligation) -> bool:
    """Return whether a replacement must semantically entail the complete source claim."""

    return obligation in _SOURCE_ENTAILMENT_REQUIRED
