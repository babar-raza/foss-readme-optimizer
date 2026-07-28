"""Define independent README review roles, contexts, identities, and verdict combination."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.specialists.review_finding_grounding import (
    BLIND_QUALITY_CRITERIA,
    FindingGroundingResultV1,
    GroundedReviewFindingV1,
)

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
        if self.verdict == "ACCEPT":
            if self.failed_criteria or self.sections_affected or self.required_repair:
                raise ValueError("blind-quality ACCEPT cannot carry failure details")
            if not self.findings or any(
                finding.disposition != "supports_acceptance" for finding in self.findings
            ):
                raise ValueError("blind-quality ACCEPT requires grounded supporting findings")
        if self.verdict == "REJECT_REPAIRABLE" and (
            not self.failed_criteria
            or not self.sections_affected
            or not self.required_repair.strip()
            or not self.findings
            or any(finding.disposition != "requires_repair" for finding in self.findings)
        ):
            raise ValueError("blind-quality rejection requires criteria, sections, and repair")
        if self.verdict == "SYSTEM_FAILURE" and self.findings:
            raise ValueError("blind-quality SYSTEM_FAILURE cannot carry findings")
        if any(finding.kind != "quality" for finding in self.findings):
            raise ValueError("blind-quality result may contain only quality findings")
        if any(finding.criterion not in BLIND_QUALITY_CRITERIA for finding in self.findings):
            raise ValueError("blind-quality criterion is outside visible-document authority")
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
        if self.verdict == "ACCEPT":
            if self.failed_criteria or self.sections_affected or self.required_repair:
                raise ValueError("factual-plan ACCEPT cannot carry failure details")
            if not self.findings or any(
                finding.disposition != "supports_acceptance" for finding in self.findings
            ):
                raise ValueError("factual-plan ACCEPT requires grounded supporting findings")
        if (
            self.verdict != "ACCEPT"
            and self.verdict != "SYSTEM_FAILURE"
            and (not self.failed_criteria or not self.sections_affected or not self.findings)
        ):
            raise ValueError("factual-plan failure requires criteria and sections")
        if self.verdict == "REJECT_REPAIRABLE" and any(
            finding.disposition != "requires_repair" for finding in self.findings
        ):
            raise ValueError("factual-plan repair verdict requires repair findings")
        if self.verdict in {"BLOCKED_FACT_CONFLICT", "BLOCKED_MISSING_EVIDENCE"} and any(
            finding.disposition != "blocks" for finding in self.findings
        ):
            raise ValueError("factual-plan blocked verdict requires blocking findings")
        if self.verdict == "SYSTEM_FAILURE" and self.findings:
            raise ValueError("factual-plan SYSTEM_FAILURE cannot carry findings")
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
    failed_criteria: list[str] = Field(default_factory=list)
    sections_affected: list[str] = Field(default_factory=list)
    required_repair: str = ""
    findings: list[GroundedReviewFindingV1] = Field(default_factory=list)
    grounding_validation: FindingGroundingResultV1 | None = None

    @model_validator(mode="after")
    def _persisted_evidence_matches_verdict(self) -> RoleReviewRecordV1:
        failure_details = (
            self.failed_criteria,
            self.sections_affected,
            self.required_repair.strip(),
            self.findings,
        )
        if self.verdict == "ACCEPT":
            if any(failure_details[:3]):
                raise ValueError("accepted role record cannot carry failure details")
            if not self.findings or any(
                finding.disposition != "supports_acceptance" for finding in self.findings
            ):
                raise ValueError("accepted role record requires grounded supporting findings")
        if self.verdict not in {"ACCEPT", "SYSTEM_FAILURE"} and (
            not self.failed_criteria or not self.sections_affected or not self.findings
        ):
            raise ValueError("non-accept role record requires persisted grounded findings")
        if self.verdict == "REJECT_REPAIRABLE" and any(
            finding.disposition != "requires_repair" for finding in self.findings
        ):
            raise ValueError("repair role record requires repair findings")
        if self.verdict in {"BLOCKED_FACT_CONFLICT", "BLOCKED_MISSING_EVIDENCE"} and any(
            finding.disposition != "blocks" for finding in self.findings
        ):
            raise ValueError("blocked role record requires blocking findings")
        if self.verdict == "SYSTEM_FAILURE" and self.findings:
            raise ValueError("system-failure role record cannot carry findings")
        expected_kind = "quality" if self.identity.role == "blind_quality_reviewer" else "factual"
        if self.identity.role != "author" and any(
            finding.kind != expected_kind for finding in self.findings
        ):
            raise ValueError("role record finding kind does not match reviewer role")
        if self.identity.role == "blind_quality_reviewer" and any(
            finding.criterion not in BLIND_QUALITY_CRITERIA for finding in self.findings
        ):
            raise ValueError("role record contains an unauthorized blind-quality criterion")
        if self.verdict != "SYSTEM_FAILURE":
            if self.grounding_validation is None or not self.grounding_validation.valid:
                raise ValueError("role record requires successful grounding validation")
            if set(self.grounding_validation.checked_finding_ids) != {
                finding.finding_id for finding in self.findings
            }:
                raise ValueError("role record grounding result does not cover every finding")
        return self


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


def json_hash(value: dict) -> str:
    """Public canonical hash seam for constructing factual-plan inputs."""

    return _json_hash(value)
