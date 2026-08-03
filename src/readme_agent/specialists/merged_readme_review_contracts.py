"""Define persisted contracts for one-call, two-facet independent README review."""

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewResultV1,
    CombinedReviewVerdict,
    FactualPlanReviewResultV1,
    RoleReviewRecordV1,
)
from readme_agent.state.assurance import ContentAssuranceV1


class MergedReadmeReviewResultV1(BaseModel):
    """Two real typed review facets returned by one physical reviewer call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    quality: BlindQualityReviewResultV1
    factual: FactualPlanReviewResultV1


class MergedReviewCallReceiptV1(BaseModel):
    """Bind compatibility role records to one physical merged response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    actor_id: str = Field(min_length=1)
    prompt_id: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    blind_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    factual_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_request_id: str | None = None
    provider_model: str | None = None


class CombinedReadmeReviewV1(BaseModel):
    """Deterministic fail-closed combination of both independent facets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    content_assurance: ContentAssuranceV1 = "repository_verified"
    verdict: CombinedReviewVerdict
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    blind_quality: RoleReviewRecordV1
    factual_plan: RoleReviewRecordV1
    merged_call_receipt: MergedReviewCallReceiptV1 | None = None
    identity_separation_valid: bool
    reasons: list[str]

    @model_validator(mode="after")
    def _review_assurance_and_receipt_are_consistent(self) -> "CombinedReadmeReviewV1":
        if {
            self.blind_quality.content_assurance,
            self.factual_plan.content_assurance,
        } != {self.content_assurance}:
            raise ValueError("combined review roles must use the same content assurance")
        same_actor = self.blind_quality.identity.actor_id == self.factual_plan.identity.actor_id
        same_prompt = (
            self.blind_quality.identity.prompt_id == self.factual_plan.identity.prompt_id
            and self.blind_quality.identity.prompt_sha256
            == self.factual_plan.identity.prompt_sha256
        )
        if self.identity_separation_valid and (same_actor or same_prompt):
            receipt = self.merged_call_receipt
            if not same_actor or not same_prompt or receipt is None:
                raise ValueError("shared reviewer identity requires one merged-call receipt")
            if (
                receipt.actor_id != self.blind_quality.identity.actor_id
                or receipt.prompt_id != self.blind_quality.identity.prompt_id
                or receipt.prompt_sha256 != self.blind_quality.identity.prompt_sha256
                or receipt.blind_record_sha256 != role_record_hash(self.blind_quality)
                or receipt.factual_record_sha256 != role_record_hash(self.factual_plan)
            ):
                raise ValueError("merged-call receipt does not bind both reviewer facets")
        return self


def role_record_hash(record: RoleReviewRecordV1) -> str:
    """Hash one grounded compatibility record for merged-call binding."""

    canonical = json.dumps(
        record.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
