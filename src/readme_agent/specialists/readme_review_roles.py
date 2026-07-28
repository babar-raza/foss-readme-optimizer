"""Define independent README review roles, contexts, identities, and verdict combination."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.specialists.review_finding_grounding import GroundedReviewFindingV1

ReviewRole = Literal["author", "blind_quality_reviewer", "factual_plan_reviewer"]
BlindQualityVerdict = Literal["ACCEPT", "REJECT_REPAIRABLE", "SYSTEM_FAILURE"]
FactualPlanVerdict = Literal[
    "ACCEPT",
    "REJECT_REPAIRABLE",
    "BLOCKED_FACT_CONFLICT",
    "BLOCKED_MISSING_EVIDENCE",
    "SYSTEM_FAILURE",
]
CombinedReviewVerdict = FactualPlanVerdict


class ReviewActorIdentityV1(BaseModel):
    """Stable actor and prompt identity used to prevent self-approval."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    actor_id: str = Field(min_length=1)
    role: ReviewRole
    prompt_id: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class BlindQualityReviewInputV1(BaseModel):
    """Visitor-visible context with no producer plan, facts, or acceptance verdict."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str = Field(min_length=3)
    original_readme_text: str
    candidate_readme_text: str = Field(min_length=1)
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rubric_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def _candidate_hash_matches(self) -> BlindQualityReviewInputV1:
        if sha256_hex(self.candidate_readme_text) != self.candidate_sha256:
            raise ValueError("blind-quality candidate hash does not match candidate bytes")
        return self


class FactualPlanReviewInputV1(BaseModel):
    """Fact-and-operation context with no producer or deterministic verdict."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str = Field(min_length=3)
    candidate_readme_text: str = Field(min_length=1)
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    product_facts: dict
    product_facts_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    presentation_plan: dict
    presentation_plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rubric_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def _hashes_match(self) -> FactualPlanReviewInputV1:
        if sha256_hex(self.candidate_readme_text) != self.candidate_sha256:
            raise ValueError("factual-plan candidate hash does not match candidate bytes")
        if _json_hash(self.product_facts) != self.product_facts_sha256:
            raise ValueError("factual-plan facts hash does not match facts")
        if _json_hash(self.presentation_plan) != self.presentation_plan_sha256:
            raise ValueError("factual-plan plan hash does not match plan")
        return self


class BlindQualityReviewResultV1(BaseModel):
    """Typed result for visible quality and usefulness only."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: BlindQualityVerdict
    reasoning: str = Field(min_length=1)
    failed_criteria: list[str] = Field(default_factory=list)
    sections_affected: list[str] = Field(default_factory=list)
    required_repair: str = ""
    findings: list[GroundedReviewFindingV1]

    @model_validator(mode="after")
    def _verdict_payload(self) -> BlindQualityReviewResultV1:
        if self.verdict == "ACCEPT" and (
            self.failed_criteria or self.sections_affected or self.required_repair or self.findings
        ):
            raise ValueError("blind-quality ACCEPT cannot carry failure details")
        if self.verdict == "REJECT_REPAIRABLE" and (
            not self.failed_criteria
            or not self.sections_affected
            or not self.required_repair.strip()
            or not self.findings
        ):
            raise ValueError("blind-quality rejection requires criteria, sections, and repair")
        if any(finding.kind != "quality" for finding in self.findings):
            raise ValueError("blind-quality result may contain only quality findings")
        return self


class FactualPlanReviewResultV1(BaseModel):
    """Typed result for claim grounding and plan-to-candidate agreement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: FactualPlanVerdict
    reasoning: str = Field(min_length=1)
    failed_criteria: list[str] = Field(default_factory=list)
    sections_affected: list[str] = Field(default_factory=list)
    required_repair: str = ""
    findings: list[GroundedReviewFindingV1]

    @model_validator(mode="after")
    def _verdict_payload(self) -> FactualPlanReviewResultV1:
        if self.verdict == "ACCEPT" and (
            self.failed_criteria or self.sections_affected or self.required_repair or self.findings
        ):
            raise ValueError("factual-plan ACCEPT cannot carry failure details")
        if (
            self.verdict != "ACCEPT"
            and self.verdict != "SYSTEM_FAILURE"
            and (not self.failed_criteria or not self.sections_affected or not self.findings)
        ):
            raise ValueError("factual-plan failure requires criteria and sections")
        if any(finding.kind != "factual" for finding in self.findings):
            raise ValueError("factual-plan result may contain only factual findings")
        if self.verdict == "BLOCKED_FACT_CONFLICT" and not any(
            finding.polarity_result == "contradicts" for finding in self.findings
        ):
            raise ValueError("fact-conflict verdict requires a contradicted factual finding")
        if self.verdict == "BLOCKED_MISSING_EVIDENCE" and not any(
            finding.polarity_result == "missing" for finding in self.findings
        ):
            raise ValueError("missing-evidence verdict requires a missing factual finding")
        return self


class RoleReviewRecordV1(BaseModel):
    """One immutable role result bound to exact candidate and prompt inputs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: ReviewActorIdentityV1
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    verdict: FactualPlanVerdict
    reasoning: str


class CombinedReadmeReviewV1(BaseModel):
    """Deterministic fail-closed combination of both independent role records."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: CombinedReviewVerdict
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    blind_quality: RoleReviewRecordV1
    factual_plan: RoleReviewRecordV1
    identity_separation_valid: bool
    reasons: list[str]


def _json_hash(value: dict) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def input_hash(value: BaseModel) -> str:
    """Hash one typed input using canonical JSON."""

    return _json_hash(value.model_dump(mode="json"))


def combine_review_verdicts(
    *,
    author: ReviewActorIdentityV1,
    blind_quality: RoleReviewRecordV1,
    factual_plan: RoleReviewRecordV1,
) -> CombinedReadmeReviewV1:
    """Combine two role verdicts without allowing producer or role identity overlap."""

    identities_valid = (
        author.role == "author"
        and blind_quality.identity.role == "blind_quality_reviewer"
        and factual_plan.identity.role == "factual_plan_reviewer"
        and len(
            {
                author.actor_id,
                blind_quality.identity.actor_id,
                factual_plan.identity.actor_id,
            }
        )
        == 3
        and blind_quality.identity.prompt_id != factual_plan.identity.prompt_id
        and blind_quality.identity.prompt_sha256 != factual_plan.identity.prompt_sha256
        and blind_quality.candidate_sha256 == factual_plan.candidate_sha256
    )
    reasons = [
        f"blind_quality:{blind_quality.verdict}:{blind_quality.reasoning}",
        f"factual_plan:{factual_plan.verdict}:{factual_plan.reasoning}",
    ]
    if not identities_valid:
        return CombinedReadmeReviewV1(
            verdict="SYSTEM_FAILURE",
            candidate_sha256=blind_quality.candidate_sha256,
            blind_quality=blind_quality,
            factual_plan=factual_plan,
            identity_separation_valid=False,
            reasons=["review identity or candidate separation failed", *reasons],
        )

    verdicts = {blind_quality.verdict, factual_plan.verdict}
    precedence: tuple[CombinedReviewVerdict, ...] = (
        "SYSTEM_FAILURE",
        "BLOCKED_FACT_CONFLICT",
        "BLOCKED_MISSING_EVIDENCE",
        "REJECT_REPAIRABLE",
        "ACCEPT",
    )
    verdict = next(item for item in precedence if item in verdicts)
    return CombinedReadmeReviewV1(
        verdict=verdict,
        candidate_sha256=blind_quality.candidate_sha256,
        blind_quality=blind_quality,
        factual_plan=factual_plan,
        identity_separation_valid=True,
        reasons=reasons,
    )


def json_hash(value: dict) -> str:
    """Public canonical hash seam for constructing factual-plan inputs."""

    return _json_hash(value)
