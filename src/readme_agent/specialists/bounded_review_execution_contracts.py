"""Define shared contracts and projections for bounded review execution."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.specialists.bounded_review_packets import (
    AggregateVerdictV1,
    BoundedFactualPacketV1,
    BoundedPacketResultV1,
    BoundedReviewPlanV1,
    BoundedVisitorPacketV1,
    CoverageLedgerV1,
)
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewResultV1,
    FactualPlanReviewResultV1,
)
from readme_agent.specialists.review_finding_grounding import (
    FindingGroundingResultV1,
)
from readme_agent.specialists.review_role_execution import normalize_redundant_role_fields


class BoundedReviewExecutionV1(BaseModel):
    """Complete packet execution and its projection into the established role contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan: BoundedReviewPlanV1
    coverage_ledger: CoverageLedgerV1
    packet_results: tuple[BoundedPacketResultV1, ...]
    aggregate: AggregateVerdictV1
    blind_result: BlindQualityReviewResultV1
    factual_result: FactualPlanReviewResultV1
    blind_grounding: FindingGroundingResultV1
    factual_grounding: FindingGroundingResultV1
    grounding_history: tuple[dict, ...] = ()


def canonical_review_json(value: dict) -> str:
    """Serialize bounded prompt context deterministically."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_bounded_packet_result(
    packet: BoundedFactualPacketV1 | BoundedVisitorPacketV1,
    result: BlindQualityReviewResultV1 | FactualPlanReviewResultV1,
) -> BoundedPacketResultV1:
    """Bind a role result to its packet identity and normalized finding anchors."""

    prefix = packet.packet_id.replace("-", ".")
    findings = [
        finding.model_copy(
            update={
                "finding_id": f"{prefix}.{finding.finding_id}",
                "section": packet.section_path,
                "candidate_anchor_id": None,
            }
        )
        for finding in result.findings
    ]
    return BoundedPacketResultV1(
        packet_id=packet.packet_id,
        facet=packet.facet,
        candidate_sha256=packet.candidate_sha256,
        packet_sha256=packet.packet_sha256,
        prompt_contract_hash=packet.prompt_contract_hash,
        input_contract_hash=packet.input_contract_hash,
        verdict=result.verdict,
        reasoning=result.reasoning,
        failed_criteria=tuple(result.failed_criteria),
        required_repair=result.required_repair,
        findings=tuple(findings),
    )


def project_bounded_role_result(
    results: Sequence[BoundedPacketResultV1],
    *,
    facet: Literal["visitor", "factual"],
) -> BlindQualityReviewResultV1 | FactualPlanReviewResultV1:
    """Reduce bounded packet results into the established role contract."""

    precedence = (
        "SYSTEM_FAILURE",
        "BLOCKED_FACT_CONFLICT",
        "BLOCKED_MISSING_EVIDENCE",
        "REJECT_REPAIRABLE",
        "ACCEPT",
    )
    allowed_visitor_verdicts = {"SYSTEM_FAILURE", "REJECT_REPAIRABLE", "ACCEPT"}
    verdicts = {result.verdict for result in results}
    verdict = next(item for item in precedence if item in verdicts)
    if facet == "visitor" and verdict not in allowed_visitor_verdicts:
        verdict = "SYSTEM_FAILURE"

    selected = [result for result in results if result.verdict == verdict]
    findings = [finding for result in selected for finding in result.findings]
    payload = normalize_redundant_role_fields(
        "blind_quality" if facet == "visitor" else "factual_plan",
        {
            "verdict": verdict,
            "reasoning": (
                f"Bounded {facet} review reduced {len(results)} packet result(s): "
                + "; ".join(result.reasoning for result in selected)
            ),
            "failed_criteria": [
                criterion for result in selected for criterion in result.failed_criteria
            ],
            "sections_affected": [finding.section for finding in findings],
            "required_repair": " ".join(
                result.required_repair for result in selected if result.required_repair.strip()
            ),
            "findings": [finding.model_dump(mode="json") for finding in findings],
        },
    )
    if facet == "visitor":
        return BlindQualityReviewResultV1.model_validate(payload)
    return FactualPlanReviewResultV1.model_validate(payload)


__all__ = [
    "BoundedReviewExecutionV1",
    "build_bounded_packet_result",
    "canonical_review_json",
    "project_bounded_role_result",
]
