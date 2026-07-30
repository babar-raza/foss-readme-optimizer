"""Versioned proposal contracts for trusted and repository-verified effects."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.capabilities.schema import OrgRepoRef
from readme_agent.state.assurance import ContentAssuranceV1


class TrustedTransformationProposalV1(BaseModel):
    """Immutable effect request for one accepted trusted README candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    proposal_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_repository: OrgRepoRef
    target_repository: OrgRepoRef
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    proposal_kind: Literal["trusted_readme_transform"] = "trusted_readme_transform"
    source_revision: str = Field(min_length=1)
    target_base_revision: str = Field(min_length=1)
    source_readme_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    facts_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    plan_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    deterministic_validation_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    independent_review_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    cohort_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_id: str = Field(min_length=1)
    expires_at: str

    @model_validator(mode="after")
    def _not_expired(self) -> "TrustedTransformationProposalV1":
        if datetime.fromisoformat(self.expires_at) <= datetime.now(UTC):
            raise ValueError("trusted transformation proposal is expired")
        return self


class OpenProposalV2(BaseModel):
    """Durable reconciled state for one stable proposal branch and draft PR."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[2] = 2
    proposal_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    domain: str = "readme_presentation"
    source_repository: OrgRepoRef
    target_repository: OrgRepoRef
    content_assurance: ContentAssuranceV1
    proposal_kind: Literal["trusted_readme_transform", "verified_repository_presentation"]
    base_revision: str
    head_revision: str
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    branch_name: str
    pr_number: int
    pr_url: str
    state: Literal["draft_open", "merged", "closed", "superseded"] = "draft_open"
    drift_status: Literal["current", "base_moved", "candidate_changed", "unknown"] = "current"
    authorization_id: str
    opened_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_reconciled_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @model_validator(mode="after")
    def _kind_matches_assurance(self) -> "OpenProposalV2":
        expected = (
            "trusted_readme_transform"
            if self.content_assurance == "trusted_inherited"
            else "verified_repository_presentation"
        )
        if self.proposal_kind != expected:
            raise ValueError(f"{self.content_assurance} requires proposal_kind={expected!r}")
        return self
