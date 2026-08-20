"""Facts-only README-section readiness: for one repository's already-collected
`ProductFactsV2`, report per-required-section sufficiency without generating a
candidate or calling an authoring model.

Section sufficiency, not corpus completeness: a repository does not need
every imported claim or every catalog member to verify -- it needs enough
truthful, accepted facts to cover each required visitor-facing section. This
reuses the existing `affected_surfaces`/accepted-fact machinery
(`agentic_composition_grounding.accepted_composition_fact_ids`,
`FactRecordV2.affected_surfaces`) rather than a parallel readiness model.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_grounding import accepted_composition_fact_ids

SectionReadiness = Literal["READY", "DEGRADED_PRESERVE_SOURCE", "BLOCKED_FACTS"]

# The nine required visitor-facing section surfaces, mapped onto the
# existing `readme.*` affected-surface vocabulary every FactRecordV2 already
# declares (facts/migration.py::SURFACE_DEPENDENCIES is the same vocabulary,
# for the legacy V1->V2 migration path; this is the current one).
REQUIRED_README_SECTIONS: dict[str, tuple[str, ...]] = {
    "identity_and_purpose": ("readme.opening",),
    "installation_coordinates": ("readme.installation",),
    "key_capabilities_formats": ("readme.capabilities", "readme.at_a_glance"),
    "dependencies_prerequisites": ("readme.dependencies",),
    "verified_example_availability": ("readme.example", "readme.examples"),
    "public_api_reference": ("readme.api_reference",),
    "scope_and_limitations": ("readme.limitations",),
    "resources_enterprise_relationship": ("readme.resources", "readme.relationship"),
    "mit_policy_statement": ("readme.license",),
}


class SectionFactsReadinessV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    section_id: str
    status: SectionReadiness
    accepted_fact_ids: tuple[str, ...]
    verified_limitation_fact_ids: tuple[str, ...]
    conflicting_fact_ids: tuple[str, ...]
    missing_fact_reason: str | None = None


class RepositoryFactsReadinessV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str
    family: str
    platform: str
    source_revision: str | None
    knowledge_revision: str | None
    freshness: str
    sections: tuple[SectionFactsReadinessV1, ...]
    overall_status: SectionReadiness

    def section(self, section_id: str) -> SectionFactsReadinessV1:
        return next(section for section in self.sections if section.section_id == section_id)


def _section_status(
    accepted_ids: tuple[str, ...], conflicting_ids: tuple[str, ...]
) -> SectionReadiness:
    """A section needs at least one accepted fact to be usable at all.
    Conflicting evidence on top of an otherwise-accepted section degrades it
    to preserve-source rather than blocking outright -- the section can
    still render from what is genuinely accepted, but the candidate must
    not silently resolve the disagreement on the author's behalf."""

    if not accepted_ids:
        return "BLOCKED_FACTS"
    if conflicting_ids:
        return "DEGRADED_PRESERVE_SOURCE"
    return "READY"


def _overall_status(sections: tuple[SectionFactsReadinessV1, ...]) -> SectionReadiness:
    if any(section.status == "BLOCKED_FACTS" for section in sections):
        return "BLOCKED_FACTS"
    if any(section.status == "DEGRADED_PRESERVE_SOURCE" for section in sections):
        return "DEGRADED_PRESERVE_SOURCE"
    return "READY"


def build_repository_facts_readiness(
    facts: ProductFactsV2,
    *,
    family: str,
    platform: str,
    source_revision: str | None,
    knowledge_revision: str | None,
    freshness: str,
) -> RepositoryFactsReadinessV1:
    """Section sufficiency, not corpus completeness: every required section
    is independently scored from whichever accepted facts actually declare
    that surface -- a section can be READY while other, unrelated imported
    claims or API members remain unverified elsewhere in the same product."""

    accepted_ids = accepted_composition_fact_ids(facts)
    sections: list[SectionFactsReadinessV1] = []
    for section_id, surfaces in REQUIRED_README_SECTIONS.items():
        surface_set = set(surfaces)
        matching = [fact for fact in facts.facts if surface_set & set(fact.affected_surfaces)]
        accepted = tuple(sorted(fact.fact_id for fact in matching if fact.fact_id in accepted_ids))
        conflicting = tuple(
            sorted(
                fact.fact_id
                for fact in matching
                if fact.verification_state == "conflicting" or fact.has_unresolved_conflict
            )
        )
        verified_limitations = tuple(
            sorted(
                fact.fact_id
                for fact in matching
                if fact.fact_id in accepted_ids
                and (
                    fact.field == "product.limitations" or fact.field.endswith("limitation_claims")
                )
            )
        )
        status = _section_status(accepted, conflicting)
        sections.append(
            SectionFactsReadinessV1(
                section_id=section_id,
                status=status,
                accepted_fact_ids=accepted,
                verified_limitation_fact_ids=verified_limitations,
                conflicting_fact_ids=conflicting,
                missing_fact_reason=(
                    None
                    if status != "BLOCKED_FACTS"
                    else f"no accepted fact declares {sorted(surface_set)!r}"
                ),
            )
        )
    return RepositoryFactsReadinessV1(
        org_repo=facts.org_repo,
        family=family,
        platform=platform,
        source_revision=source_revision,
        knowledge_revision=knowledge_revision,
        freshness=freshness,
        sections=tuple(sections),
        overall_status=_overall_status(tuple(sections)),
    )


__all__ = [
    "REQUIRED_README_SECTIONS",
    "RepositoryFactsReadinessV1",
    "SectionFactsReadinessV1",
    "SectionReadiness",
    "build_repository_facts_readiness",
]
