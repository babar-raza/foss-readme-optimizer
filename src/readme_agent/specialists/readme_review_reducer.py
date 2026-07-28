"""Reduce independently grounded reviewer records into lifecycle authority."""

from __future__ import annotations

from pydantic import Field

from readme_agent.specialists.independent_readme_review import IndependentReadmeReviewResultV1
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewResultV1,
    CombinedReadmeReviewV1,
    CombinedReviewVerdict,
    FactualPlanReviewResultV1,
    FactualPlanVerdict,
    ReviewActorIdentityV1,
    RoleReviewRecordV1,
)
from readme_agent.specialists.review_finding_grounding import (
    FindingGroundingResultV1,
    GroundedReviewFindingV1,
)


class SeparatedReadmeReviewResultV1(IndependentReadmeReviewResultV1):
    """Compatibility verdict plus both immutable role records and their reduction."""

    blind_quality_review: RoleReviewRecordV1
    factual_plan_review: RoleReviewRecordV1
    combined_review: CombinedReadmeReviewV1
    grounding_retry_history: list[dict]
    review_contract_version: str = Field(default="2", frozen=True)


def build_role_review_record(
    *,
    identity: ReviewActorIdentityV1,
    candidate_sha256: str,
    input_sha256: str,
    verdict: FactualPlanVerdict,
    reasoning: str,
    failed_criteria: list[str],
    sections_affected: list[str],
    required_repair: str,
    findings: list[GroundedReviewFindingV1],
    grounding_validation: FindingGroundingResultV1,
) -> RoleReviewRecordV1:
    """Persist one role result with its deterministic grounding receipt."""

    return RoleReviewRecordV1(
        identity=identity,
        candidate_sha256=candidate_sha256,
        input_sha256=input_sha256,
        verdict=verdict,
        reasoning=reasoning,
        failed_criteria=failed_criteria,
        sections_affected=sections_affected,
        required_repair=required_repair,
        findings=findings,
        grounding_validation=grounding_validation,
    )


def combine_review_verdicts(
    *,
    author: ReviewActorIdentityV1,
    blind_quality: RoleReviewRecordV1,
    factual_plan: RoleReviewRecordV1,
) -> CombinedReadmeReviewV1:
    """Combine role verdicts without allowing producer or reviewer identity overlap."""

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
        _authoritative_role_reason("blind_quality", blind_quality),
        _authoritative_role_reason("factual_plan", factual_plan),
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


def build_compatibility_result(
    blind: BlindQualityReviewResultV1,
    factual: FactualPlanReviewResultV1,
    blind_record: RoleReviewRecordV1,
    factual_record: RoleReviewRecordV1,
    combined: CombinedReadmeReviewV1,
    grounding_retry_history: list[dict],
) -> SeparatedReadmeReviewResultV1:
    """Project the separated result through the legacy independent-review seam."""

    failed_criteria = sorted({*blind.failed_criteria, *factual.failed_criteria})
    sections_affected = sorted({*blind.sections_affected, *factual.sections_affected})
    repairs = [
        (
            f"Revise {finding.section} for {finding.criterion} around exact span: "
            f"{finding.quoted_candidate_span}"
            if finding.kind == "quality"
            else finding.required_repair.strip()
        )
        for finding in [*blind.findings, *factual.findings]
        if finding.disposition == "requires_repair"
    ]
    return SeparatedReadmeReviewResultV1(
        verdict=combined.verdict,
        reasoning="; ".join(combined.reasons),
        failed_criteria=failed_criteria,
        sections_affected=sections_affected,
        required_repair="\n".join(repairs),
        preserve=[],
        blind_quality_review=blind_record,
        factual_plan_review=factual_record,
        combined_review=combined,
        grounding_retry_history=grounding_retry_history,
    )


def _authoritative_role_reason(role: str, record: RoleReviewRecordV1) -> str:
    if record.verdict in {"ACCEPT", "SYSTEM_FAILURE"}:
        return f"{role}:{record.verdict}"
    anchors = ",".join(
        f"{finding.finding_id}@{finding.section}:{finding.criterion}" for finding in record.findings
    )
    return f"{role}:{record.verdict}:{anchors}"
