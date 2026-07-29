"""Define assurance-specific contracts for independent trusted README review."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.capabilities.schema import OrgRepoRef
from readme_agent.readme.trusted_composition_models import (
    TrustedReadmeCompositionOutputV1,
    TrustedReadmeSectionRepairRequestV1,
)

TrustedReviewRoleV1 = Literal["author", "blind_quality_reviewer", "inheritance_fidelity_reviewer"]
TrustedRoleVerdictV1 = Literal["ACCEPT", "REJECT_REPAIRABLE", "SYSTEM_FAILURE"]
TrustedTransformVerdictV1 = Literal[
    "TRUSTED_TRANSFORM_APPROVED",
    "REJECT_REPAIRABLE",
    "SYSTEM_FAILURE",
]


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TrustedReviewActorIdentityV1(_StrictFrozenModel):
    """Stable role, route, and prompt identity used to prohibit self-approval."""

    actor_id: str = Field(min_length=1)
    role: TrustedReviewRoleV1
    prompt_id: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_route: str = Field(min_length=1)


class TrustedCandidateValidationV1(_StrictFrozenModel):
    """Deterministic validation receipt required before either reviewer runs."""

    schema_version: Literal[1] = 1
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    checks_passed: tuple[str, ...] = Field(min_length=1)
    passed: Literal[True] = True


class TrustedFidelitySourceCheckV1(_StrictFrozenModel):
    """One independent disposition for an inherited README source unit."""

    fact_id: str = Field(pattern=r"^readme\.inherited:[0-9a-f]{24}$")
    outcome: Literal["preserved_or_represented", "lost_or_distorted"]
    source_quote: str = Field(min_length=1)
    candidate_quote: str = ""
    section: str = Field(min_length=1)
    required_repair: str = ""

    @model_validator(mode="after")
    def _outcome_payload(self) -> TrustedFidelitySourceCheckV1:
        if self.outcome == "preserved_or_represented":
            if not self.candidate_quote or self.required_repair:
                raise ValueError("preserved source check requires a candidate quote and no repair")
        elif not self.required_repair.strip():
            raise ValueError("lost or distorted source check requires bounded repair")
        return self


class TrustedUnsupportedAdditionV1(_StrictFrozenModel):
    """One candidate addition the fidelity reviewer cannot trace to source or standards."""

    finding_id: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    section: str = Field(min_length=1)
    quoted_candidate_span: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    required_repair: str = Field(min_length=1)


class TrustedFidelityReviewResultV1(_StrictFrozenModel):
    """Typed LLM verdict over README inheritance, never repository factuality."""

    verdict: TrustedRoleVerdictV1
    reasoning: str = Field(min_length=1)
    source_checks: tuple[TrustedFidelitySourceCheckV1, ...] = ()
    unsupported_additions: tuple[TrustedUnsupportedAdditionV1, ...] = ()
    failed_criteria: tuple[str, ...] = ()
    sections_affected: tuple[str, ...] = ()
    required_repair: str = ""

    @model_validator(mode="after")
    def _verdict_payload(self) -> TrustedFidelityReviewResultV1:
        if self.verdict != "SYSTEM_FAILURE" and not self.source_checks:
            raise ValueError("fidelity decision requires inherited source checks")
        defects = any(item.outcome == "lost_or_distorted" for item in self.source_checks) or bool(
            self.unsupported_additions
        )
        if self.verdict == "ACCEPT" and (
            defects or self.failed_criteria or self.sections_affected or self.required_repair
        ):
            raise ValueError("fidelity ACCEPT cannot carry defects or repair instructions")
        if self.verdict == "REJECT_REPAIRABLE" and (
            not defects
            or not self.failed_criteria
            or not self.sections_affected
            or not self.required_repair.strip()
        ):
            raise ValueError("fidelity rejection requires grounded defects and bounded repair")
        if self.verdict == "SYSTEM_FAILURE" and not self.reasoning.strip():
            raise ValueError("fidelity SYSTEM_FAILURE requires a reason")
        return self


class TrustedReviewRoleRecordV1(_StrictFrozenModel):
    """One immutable reviewer result bound to exact inputs and candidate bytes."""

    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    identity: TrustedReviewActorIdentityV1
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    verdict: TrustedRoleVerdictV1
    result: dict


class TrustedReviewCacheIdentityV1(_StrictFrozenModel):
    """Every dependency that can invalidate a trusted review decision."""

    schema_version: Literal[1] = 1
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    org_repo: OrgRepoRef
    source_revision: str = Field(min_length=7)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fact_graph_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    transform_plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    configured_standards_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deterministic_validation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    author_prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    blind_prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fidelity_prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    author_model_route: str = Field(min_length=1)
    blind_model_route: str = Field(min_length=1)
    fidelity_model_route: str = Field(min_length=1)
    review_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


class TrustedTransformReviewV1(_StrictFrozenModel):
    """Final deterministic reduction of both independent trusted-review roles."""

    schema_version: Literal[1] = 1
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    factual_truth_verified: Literal[False] = False
    org_repo: OrgRepoRef
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation: TrustedCandidateValidationV1
    author: TrustedReviewActorIdentityV1
    blind_quality: TrustedReviewRoleRecordV1
    inheritance_fidelity: TrustedReviewRoleRecordV1
    identity_separation_valid: bool
    verdict: TrustedTransformVerdictV1
    reasons: tuple[str, ...] = Field(min_length=1)
    cache_identity: TrustedReviewCacheIdentityV1
    cache_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _bindings_match(self) -> TrustedTransformReviewV1:
        if self.cache_identity.canonical_hash() != self.cache_identity_sha256:
            raise ValueError("trusted review cache identity checksum does not match")
        hashes = {
            self.candidate_sha256,
            self.validation.candidate_sha256,
            self.blind_quality.candidate_sha256,
            self.inheritance_fidelity.candidate_sha256,
            self.cache_identity.candidate_sha256,
        }
        if len(hashes) != 1:
            raise ValueError("trusted review records refer to different candidates")
        identities_separated = (
            self.author.role == "author"
            and self.blind_quality.identity.role == "blind_quality_reviewer"
            and self.inheritance_fidelity.identity.role == "inheritance_fidelity_reviewer"
            and len(
                {
                    self.author.actor_id,
                    self.blind_quality.identity.actor_id,
                    self.inheritance_fidelity.identity.actor_id,
                }
            )
            == 3
            and len(
                {
                    self.author.prompt_sha256,
                    self.blind_quality.identity.prompt_sha256,
                    self.inheritance_fidelity.identity.prompt_sha256,
                }
            )
            == 3
        )
        if self.identity_separation_valid != identities_separated:
            raise ValueError("trusted review identity-separation claim is incorrect")
        role_verdicts = {self.blind_quality.verdict, self.inheritance_fidelity.verdict}
        expected_verdict: TrustedTransformVerdictV1 = (
            "SYSTEM_FAILURE"
            if not identities_separated or "SYSTEM_FAILURE" in role_verdicts
            else (
                "REJECT_REPAIRABLE"
                if "REJECT_REPAIRABLE" in role_verdicts
                else "TRUSTED_TRANSFORM_APPROVED"
            )
        )
        if self.verdict != expected_verdict:
            raise ValueError("trusted review verdict does not match deterministic role reduction")
        return self


class TrustedReviewExecutionV1(_StrictFrozenModel):
    """Review result plus exact per-run provider/fixture/cache accounting."""

    review: TrustedTransformReviewV1
    cache_reused: bool
    accounting_status: Literal["EXACT"] = "EXACT"
    provider_calls_before: int = Field(ge=0)
    provider_calls_after: int = Field(ge=0)
    fixture_calls_before: int = Field(ge=0)
    fixture_calls_after: int = Field(ge=0)
    cache_reuses_before: int = Field(ge=0)
    cache_reuses_after: int = Field(ge=0)
    ledger_path: str = Field(min_length=1)
    ledger_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_call_ids: tuple[str, ...] = ()
    calls_by_job: dict[str, int] = Field(default_factory=dict)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _accounting_is_monotonic(self) -> TrustedReviewExecutionV1:
        pairs = (
            (self.provider_calls_before, self.provider_calls_after),
            (self.fixture_calls_before, self.fixture_calls_after),
            (self.cache_reuses_before, self.cache_reuses_after),
        )
        if any(after < before for before, after in pairs):
            raise ValueError("trusted review accounting counters cannot decrease")
        if self.cache_reused and (
            self.review.verdict != "TRUSTED_TRANSFORM_APPROVED"
            or self.provider_calls_after != self.provider_calls_before
            or self.fixture_calls_after != self.fixture_calls_before
            or self.cache_reuses_after != self.cache_reuses_before + 1
        ):
            raise ValueError("trusted accepted-cache reuse accounting is inconsistent")
        return self

    @property
    def new_provider_call_count(self) -> int:
        return self.provider_calls_after - self.provider_calls_before


class TrustedRepairAttemptV1(_StrictFrozenModel):
    """One section-scoped changed-byte repair and its rereview result."""

    attempt: int = Field(ge=1, le=2)
    request: TrustedReadmeSectionRepairRequestV1
    candidate_sha256_before: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_sha256_after: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_changed: bool
    rereview_verdict: TrustedTransformVerdictV1 | None = None


class TrustedReviewLoopResultV1(_StrictFrozenModel):
    """Terminal trusted review/repair outcome with visible system failures."""

    outcome: Literal["accepted", "rejected", "system_failure"]
    final_composition: TrustedReadmeCompositionOutputV1
    final_execution: TrustedReviewExecutionV1
    repair_history: tuple[TrustedRepairAttemptV1, ...] = ()
    system_failure_reason: str | None = None

    @model_validator(mode="after")
    def _outcome_matches_review(self) -> TrustedReviewLoopResultV1:
        verdict = self.final_execution.review.verdict
        if self.outcome == "accepted" and verdict != "TRUSTED_TRANSFORM_APPROVED":
            raise ValueError("accepted trusted loop requires trusted approval")
        if self.outcome == "rejected" and verdict != "REJECT_REPAIRABLE":
            raise ValueError("rejected trusted loop requires repairable rejection")
        if self.outcome == "system_failure" and not self.system_failure_reason:
            raise ValueError("trusted system failure requires a visible reason")
        return self


def canonical_hash(value: object) -> str:
    """Hash one JSON-compatible review input without ambient state."""

    return _canonical_hash(value)


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
