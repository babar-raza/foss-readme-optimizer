"""Packet-result validation and fail-closed aggregation for bounded review."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import Field, model_validator

from readme_agent.specialists.bounded_review_contracts import (
    _SHA256_PATTERN,
    AggregateOverall,
    BoundedFactualPacketV1,
    BoundedPacketV1,
    BoundedPacketVerdict,
    BoundedReviewPlanV1,
    PacketFacet,
    _StrictModel,
)
from readme_agent.specialists.bounded_review_coverage import (
    CoverageLedgerV1,
    validate_coverage_ledger,
)
from readme_agent.specialists.bounded_review_hashing import _canonical_hash
from readme_agent.specialists.review_finding_grounding import (
    BLIND_QUALITY_CRITERIA,
    GroundedReviewFindingV1,
)


class BoundedPacketResultV1(_StrictModel):
    """One packet's reviewer result.

    Mirrors ``FactualPlanReviewResultV1``'s cross-field validator discipline (redesign point 6)
    instead of a looser shape: ACCEPT requires grounded ``supports_acceptance`` findings, a
    ``BLOCKED_*`` verdict requires a corresponding blocking finding, and finding ``kind`` must
    match the packet's own facet (``factual`` for factual packets, ``quality`` for visitor
    packets, restricted to ``BLIND_QUALITY_CRITERIA`` for visitor packets exactly as
    ``BlindQualityReviewResultV1`` restricts its own findings).
    """

    schema_version: Literal[1] = 1
    packet_id: str = Field(min_length=1)
    facet: PacketFacet
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    packet_sha256: str = Field(pattern=_SHA256_PATTERN)
    prompt_contract_hash: str = Field(pattern=_SHA256_PATTERN)
    input_contract_hash: str = Field(pattern=_SHA256_PATTERN)
    verdict: BoundedPacketVerdict
    reasoning: str = Field(min_length=1)
    failed_criteria: tuple[str, ...] = ()
    required_repair: str = ""
    findings: tuple[GroundedReviewFindingV1, ...] = ()

    @model_validator(mode="after")
    def _verdict_payload(self) -> BoundedPacketResultV1:
        if self.verdict == "ACCEPT":
            if self.failed_criteria or self.required_repair:
                raise ValueError("bounded packet ACCEPT cannot carry failure details")
            if not self.findings or any(
                finding.disposition != "supports_acceptance" for finding in self.findings
            ):
                raise ValueError("bounded packet ACCEPT requires grounded supporting findings")
        if (
            self.verdict != "ACCEPT"
            and self.verdict != "SYSTEM_FAILURE"
            and (not self.failed_criteria or not self.findings)
        ):
            raise ValueError("bounded packet failure requires criteria and findings")
        if self.verdict == "REJECT_REPAIRABLE" and any(
            finding.disposition != "requires_repair" for finding in self.findings
        ):
            raise ValueError("bounded packet repair verdict requires repair findings")
        if self.verdict in {"BLOCKED_FACT_CONFLICT", "BLOCKED_MISSING_EVIDENCE"} and any(
            finding.disposition != "blocks" for finding in self.findings
        ):
            raise ValueError("bounded packet blocked verdict requires blocking findings")
        if self.verdict == "SYSTEM_FAILURE" and self.findings:
            raise ValueError("bounded packet SYSTEM_FAILURE cannot carry findings")
        expected_kind = "quality" if self.facet == "visitor" else "factual"
        if any(finding.kind != expected_kind for finding in self.findings):
            raise ValueError("bounded packet result finding kind does not match packet facet")
        if self.facet == "visitor" and any(
            finding.criterion not in BLIND_QUALITY_CRITERIA for finding in self.findings
        ):
            raise ValueError(
                "bounded visitor packet criterion is outside visible-quality authority"
            )
        if self.verdict == "BLOCKED_FACT_CONFLICT" and not any(
            finding.polarity_result == "contradicts" for finding in self.findings
        ):
            raise ValueError("fact-conflict verdict requires a contradicted factual finding")
        if self.verdict == "BLOCKED_MISSING_EVIDENCE" and not any(
            finding.polarity_result == "missing" for finding in self.findings
        ):
            raise ValueError("missing-evidence verdict requires a missing factual finding")
        return self


class PacketResultValidationV1(_StrictModel):
    """Never-raising structural validation result for one packet result against its plan."""

    valid: bool
    errors: tuple[str, ...] = ()


def _find_packet(plan: BoundedReviewPlanV1, packet_id: str) -> BoundedPacketV1 | None:
    all_packets: tuple[BoundedPacketV1, ...] = (*plan.factual_packets, *plan.visitor_packets)
    for packet in all_packets:
        if packet.packet_id == packet_id:
            return packet
    return None


def _packet_text(packet: BoundedPacketV1) -> str:
    if isinstance(packet, BoundedFactualPacketV1):
        return packet.unit_text
    return packet.neighbor_context_before + packet.section_text + packet.neighbor_context_after


def validate_packet_result(
    plan: BoundedReviewPlanV1,
    result: BoundedPacketResultV1,
) -> PacketResultValidationV1:
    """Never raises. Checks packet existence, hash echoes, and finding containment.

    A finding's ``quoted_candidate_span`` must occur within the packet's own declared text, its
    ``section`` must match the packet's ``section_path``, and (for factual packets) its
    ``fact_id`` must be one of the packet's own ``accepted_fact_ids`` -- this is what rejects a
    finding that "refers outside its span."
    """

    errors: list[str] = []
    packet = _find_packet(plan, result.packet_id)
    if packet is None:
        return PacketResultValidationV1(
            valid=False, errors=(f"{result.packet_id}: packet does not exist in plan",)
        )
    if result.facet != packet.facet:
        errors.append(f"{result.packet_id}: facet does not match plan packet")
    if result.candidate_sha256 != packet.candidate_sha256:
        errors.append(f"{result.packet_id}: candidate_sha256 does not match plan packet")
    if result.packet_sha256 != packet.packet_sha256:
        errors.append(f"{result.packet_id}: packet_sha256 does not match plan packet (stale)")
    if result.prompt_contract_hash != packet.prompt_contract_hash:
        errors.append(f"{result.packet_id}: prompt_contract_hash does not match plan packet")
    if result.input_contract_hash != packet.input_contract_hash:
        errors.append(f"{result.packet_id}: input_contract_hash does not match plan packet")

    packet_text = _packet_text(packet)
    allowed_fact_ids = (
        set(packet.accepted_fact_ids) if isinstance(packet, BoundedFactualPacketV1) else set()
    )
    for finding in result.findings:
        if finding.quoted_candidate_span not in packet_text:
            errors.append(
                f"{finding.finding_id}: quoted span is outside this packet's declared text"
            )
        if finding.section != packet.section_path:
            errors.append(
                f"{finding.finding_id}: finding section does not match packet section_path"
            )
        if finding.fact_id is not None and finding.fact_id not in allowed_fact_ids:
            errors.append(
                f"{finding.finding_id}: fact_id is outside this packet's accepted fact set"
            )
    return PacketResultValidationV1(valid=not errors, errors=tuple(errors))


class AggregateVerdictV1(_StrictModel):
    """One deterministic, fail-closed reduction of every packet result for a plan.

    ``BLOCKED`` is checked first and independently of every packet result (redesign point 5):
    no amount of complete, valid, ACCEPT packet results can rescue a structurally unreviewable
    plan. ``ACCEPT`` requires every required packet present, valid, and ACCEPT, with no conflicts
    -- the default is never ACCEPT.
    """

    schema_version: Literal[1] = 1
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_hash: str = Field(pattern=_SHA256_PATTERN)
    overall: AggregateOverall
    accepted_packet_ids: tuple[str, ...] = ()
    missing_packet_ids: tuple[str, ...] = ()
    invalid_packet_ids: tuple[str, ...] = ()
    rejected_packet_ids: tuple[str, ...] = ()
    conflicting_packet_ids: tuple[str, ...] = ()
    blocking_record_ids: tuple[str, ...] = ()
    details: tuple[str, ...] = ()

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


def aggregate_packet_results(
    plan: BoundedReviewPlanV1,
    coverage_ledger: CoverageLedgerV1,
    results: Mapping[str, BoundedPacketResultV1],
) -> AggregateVerdictV1:
    """Reduce every packet result to one fail-closed aggregate verdict. Never raises."""

    required_ids = {p.packet_id for p in plan.factual_packets} | {
        p.packet_id for p in plan.visitor_packets
    }
    blocking_record_ids = tuple(sorted(record.record_id for record in plan.unpacketizable))
    ledger_blocked = validate_coverage_ledger(coverage_ledger).has_blocking_gaps
    if ledger_blocked or blocking_record_ids:
        return AggregateVerdictV1(
            candidate_sha256=plan.candidate_sha256,
            plan_hash=plan.plan_hash,
            overall="BLOCKED",
            blocking_record_ids=blocking_record_ids,
            missing_packet_ids=tuple(sorted(required_ids - set(results))),
            details=("plan has unpacketizable records; more reviewer calls cannot resolve this",),
        )

    missing_ids = sorted(required_ids - set(results))
    invalid_ids = sorted(
        packet_id
        for packet_id in required_ids
        if packet_id not in missing_ids
        and not validate_packet_result(plan, results[packet_id]).valid
    )
    if missing_ids or invalid_ids:
        return AggregateVerdictV1(
            candidate_sha256=plan.candidate_sha256,
            plan_hash=plan.plan_hash,
            overall="INCOMPLETE",
            missing_packet_ids=tuple(missing_ids),
            invalid_packet_ids=tuple(invalid_ids),
        )

    conflicting_ids: set[str] = set()
    for overlap in coverage_ledger.overlaps:
        involved = [packet_id for packet_id in overlap.packet_ids if packet_id in results]
        if len(involved) < 2:
            continue
        verdicts = {results[packet_id].verdict for packet_id in involved}
        if len(verdicts) > 1:
            conflicting_ids.update(involved)
    if conflicting_ids:
        return AggregateVerdictV1(
            candidate_sha256=plan.candidate_sha256,
            plan_hash=plan.plan_hash,
            overall="CONFLICT",
            conflicting_packet_ids=tuple(sorted(conflicting_ids)),
        )

    rejected_ids = sorted(
        packet_id for packet_id in required_ids if results[packet_id].verdict != "ACCEPT"
    )
    if rejected_ids:
        return AggregateVerdictV1(
            candidate_sha256=plan.candidate_sha256,
            plan_hash=plan.plan_hash,
            overall="REJECTED",
            rejected_packet_ids=tuple(rejected_ids),
        )

    return AggregateVerdictV1(
        candidate_sha256=plan.candidate_sha256,
        plan_hash=plan.plan_hash,
        overall="ACCEPT",
        accepted_packet_ids=tuple(sorted(required_ids)),
    )
