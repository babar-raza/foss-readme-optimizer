"""Per-surface missing/conflicting fact gates and claim-citation validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.facts.schema_v2 import ProductFactsV2

_ACCEPTED_STATES = {"verified", "policy_approved"}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SurfaceFactRequirementV1(_StrictModel):
    surface_id: str
    required_fields: list[str] = Field(min_length=1)


class SurfaceFactDecisionV1(_StrictModel):
    surface_id: str
    eligible: bool
    blocking_fact_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class TechnicalClaimV1(_StrictModel):
    claim_id: str
    surface_id: str
    text: str
    fact_ids: list[str] = Field(min_length=1)


class ClaimCitationDecisionV1(_StrictModel):
    valid: bool
    invalid_claim_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


def evaluate_surface_facts(
    facts: ProductFactsV2, requirements: list[SurfaceFactRequirementV1]
) -> list[SurfaceFactDecisionV1]:
    decisions = []
    for requirement in requirements:
        blocking_ids = []
        reasons = []
        for field_name in requirement.required_fields:
            try:
                fact = facts.selected_fact(field_name)
            except KeyError:
                blocking_ids.append(f"{field_name}:absent")
                reasons.append(f"{field_name}: no selected fact")
                continue
            if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
                blocking_ids.append(fact.fact_id)
                reasons.append(f"{field_name}: {fact.verification_state}")
        decisions.append(
            SurfaceFactDecisionV1(
                surface_id=requirement.surface_id,
                eligible=not blocking_ids,
                blocking_fact_ids=blocking_ids,
                reasons=reasons,
            )
        )
    return decisions


def validate_claim_citations(
    facts: ProductFactsV2, claims: list[TechnicalClaimV1]
) -> ClaimCitationDecisionV1:
    invalid = []
    reasons = []
    for claim in claims:
        claim_invalid = False
        for fact_id in claim.fact_ids:
            try:
                fact = facts.fact_by_id(fact_id)
            except KeyError:
                claim_invalid = True
                reasons.append(f"{claim.claim_id}: unknown fact {fact_id}")
                continue
            selected_fact_id = facts.selected_fact_ids.get(fact.field)
            if selected_fact_id != fact_id:
                claim_invalid = True
                reasons.append(f"{claim.claim_id}: fact {fact_id} is not selected for {fact.field}")
            if claim.surface_id not in fact.affected_surfaces:
                claim_invalid = True
                reasons.append(
                    f"{claim.claim_id}: fact {fact_id} does not govern {claim.surface_id}"
                )
            if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
                claim_invalid = True
                reasons.append(f"{claim.claim_id}: fact {fact_id} is {fact.verification_state}")
        if claim_invalid:
            invalid.append(claim.claim_id)
    return ClaimCitationDecisionV1(
        valid=not invalid,
        invalid_claim_ids=invalid,
        reasons=reasons,
    )
