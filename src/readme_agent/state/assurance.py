"""Define assurance identities shared by lifecycle, evidence, proposal, and effect state."""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

ContentAssuranceV1 = Literal["trusted_inherited", "repository_verified"]

TrustedReadmePocStatusV1 = Literal[
    "TRUSTED_FACTS_EXTRACTING",
    "TRUSTED_FACTS_EXTRACTED",
    "TRUSTED_PLAN_READY",
    "TRUSTED_CANDIDATE_GENERATED",
    "TRUSTED_DETERMINISTIC_VALIDATED",
    "TRUSTED_REVIEWING",
    "TRUSTED_REVIEW_REJECTED",
    "TRUSTED_REPAIRING",
    "TRUSTED_TRANSFORM_APPROVED",
    "TRUSTED_NO_OP_PROVEN",
    "TRUSTED_PR_ELIGIBLE",
    "TRUSTED_PR_OPEN",
]

TRUSTED_README_STATUSES = frozenset(get_args(TrustedReadmePocStatusV1))
VERIFIED_APPROVAL_STATUSES = frozenset(
    {
        "AGENT_APPROVED",
        "NO_OP_PROVEN",
        "HUMAN_REVIEW_READY",
        "HUMAN_ACCEPTED",
        "PR_ELIGIBLE",
        "PR_PROOF_COMPLETE",
    }
)


class AssuranceBoundProposalIdentityV1(BaseModel):
    """Identity that prevents a trusted proposal from satisfying a verified effect."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    content_assurance: ContentAssuranceV1
    org_repo: str = Field(pattern=r"^[^/]+/[^/]+$")
    source_revision: str = Field(min_length=1)
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    facts_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    proposal_kind: Literal["trusted_readme_transform", "verified_repository_presentation"]

    @model_validator(mode="after")
    def _kind_matches_assurance(self) -> AssuranceBoundProposalIdentityV1:
        expected = (
            "trusted_readme_transform"
            if self.content_assurance == "trusted_inherited"
            else "verified_repository_presentation"
        )
        if self.proposal_kind != expected:
            raise ValueError(
                f"{self.content_assurance} assurance requires proposal_kind={expected!r}"
            )
        return self


def require_verified_assurance(content_assurance: ContentAssuranceV1, *, boundary: str) -> None:
    """Fail closed when trusted content attempts to cross a verified-only boundary."""

    if content_assurance != "repository_verified":
        raise ValueError(
            f"{boundary} requires repository_verified assurance; got {content_assurance}"
        )
