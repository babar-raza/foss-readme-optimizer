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
    "authoritative_owner_validation",
    "explicit_uncertainty",
    "required_correction",
    "unjustified_loss",
    "unbound_generated",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


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
    authoritative_owners: list[str] = Field(default_factory=list)
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
