"""Typed contracts for complete README claim-accountability inventories."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.readme.assessment_claims import ClaimDisposition

ClaimStage = Literal["source", "candidate"]
ClaimOrigin = Literal["inherited", "generated"]
ExpectedClaimDisposition = Literal[
    "accepted_fact",
    "configured_standard",
    "deferred_verification",
    "verified_omission",
    "verified_equivalence",
    "verified_obligation_replacement",
    "authoritative_owner_validation",
    "explicit_uncertainty",
    "required_correction",
    "unjustified_loss",
    "unbound_generated",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StructuredFactCoordinateV1(_StrictModel):
    """One exact visitor-meaningful coordinate inside a selected typed fact."""

    fact_id: str
    field: str
    path: str
    value_sha256: str
    normalization_version: Literal["structured-fact-coordinate-v1"] = (
        "structured-fact-coordinate-v1"
    )


class EquivalentCandidateClaimV1(_StrictModel):
    """Exact candidate claim contributing to a structured source equivalence."""

    claim_id: str
    candidate_byte_start: int = Field(ge=0)
    candidate_byte_end: int = Field(ge=0)
    content_sha256: str
    fact_coordinates: list[StructuredFactCoordinateV1] = Field(min_length=1)


class ReadmeClaimAccountabilityV1(_StrictModel):
    """Expected accountability for one exact material content unit."""

    claim_id: str
    stage: ClaimStage
    origin: ClaimOrigin
    source_byte_start: int = Field(ge=0)
    source_byte_end: int = Field(ge=0)
    content_sha256: str
    current_disposition: ClaimDisposition
    accepted_fact_ids: list[str] = Field(default_factory=list)
    accepted_fact_coordinates: list[StructuredFactCoordinateV1] = Field(default_factory=list)
    configured_standard_ids: list[str] = Field(default_factory=list)
    authoritative_owners: list[str] = Field(default_factory=list)
    equivalence_group_id: str | None = None
    equivalent_source_claim_ids: list[str] = Field(default_factory=list)
    equivalent_candidate_claims: list[EquivalentCandidateClaimV1] = Field(default_factory=list)
    equivalence_normalization_version: Literal["structured-fact-coordinate-v1"] | None = None
    survives_in_candidate: bool | None = None
    expected_disposition: ExpectedClaimDisposition
    currently_accountable: bool
    rationale: str = Field(min_length=1)


class ReadmeClaimAccountabilityMapV1(_StrictModel):
    """Complete source-and-candidate material-claim inventory."""

    schema_version: Literal[1] = 1
    org_repo: str
    facts_hash: str
    source_sha256: str
    candidate_sha256: str
    claims: list[ReadmeClaimAccountabilityV1]

    def canonical_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ClaimAccountabilityValidationV1(_StrictModel):
    """Structural completeness and approval eligibility for one claim map."""

    valid: bool
    approval_eligible: bool
    checks: dict[str, bool]
    errors: list[str] = Field(default_factory=list)
    blocking_claim_ids: list[str] = Field(default_factory=list)
