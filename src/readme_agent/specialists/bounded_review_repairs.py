"""Selective repair routing and cache invalidation for bounded review packets."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import Field

from readme_agent.specialists.bounded_review_contracts import (
    _SHA256_PATTERN,
    BoundedFactualPacketV1,
    BoundedPacketV1,
    BoundedReviewPlanV1,
    PacketFacet,
    _StrictModel,
)
from readme_agent.specialists.bounded_review_hashing import _canonical_hash
from readme_agent.specialists.bounded_review_results import (
    AggregateVerdictV1,
    BoundedPacketResultV1,
    _find_packet,
)


class RepairTargetV1(_StrictModel):
    """One narrow, deterministic repair target -- never the whole candidate."""

    packet_id: str | None = None
    facet: PacketFacet | None = None
    section_path: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    claim_ids: tuple[str, ...] = ()
    fact_ids: tuple[str, ...] = ()
    issue_summary: str = Field(min_length=1)
    required_section_authoring_clusters: tuple[str, ...] = ()


class RepairPlanV1(_StrictModel):
    """Pure data production: no retry loop, no candidate mutation, no autonomous call issuance.

    ``requires_deterministic_remediation=True`` (only set when ``aggregate.overall == "BLOCKED"``)
    is the operational payoff of redesign point 5: it tells the caller that issuing more LLM calls
    will not help, and that targets come from ``plan.unpacketizable``, not from reviewer failures.
    """

    schema_version: Literal[1] = 1
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_hash: str = Field(pattern=_SHA256_PATTERN)
    round_number: int = Field(ge=0)
    max_repair_rounds: int = Field(ge=0)
    repair_permitted: bool
    requires_deterministic_remediation: bool = False
    targets: tuple[RepairTargetV1, ...] = ()

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


def _cluster_for(
    section_path: str, section_cluster_map: Mapping[str, str] | None
) -> tuple[str, ...]:
    if section_cluster_map is None or section_path not in section_cluster_map:
        return ()
    return (section_cluster_map[section_path],)


def route_selective_repairs(
    plan: BoundedReviewPlanV1,
    aggregate: AggregateVerdictV1,
    results: Mapping[str, BoundedPacketResultV1],
    *,
    current_round: int,
    max_repair_rounds: int,
    section_cluster_map: Mapping[str, str] | None = None,
) -> RepairPlanV1:
    """Route a narrow set of deterministic repair targets. Never mutates or retries."""

    repair_permitted = current_round < max_repair_rounds

    if aggregate.overall == "BLOCKED":
        targets = tuple(
            RepairTargetV1(
                packet_id=None,
                facet=None,
                section_path=record.section_path,
                char_start=record.char_start,
                char_end=record.char_end,
                claim_ids=(record.claim_id,) if record.claim_id else (),
                fact_ids=(record.missing_fact_id,) if record.missing_fact_id else (),
                issue_summary=record.detail,
                required_section_authoring_clusters=_cluster_for(
                    record.section_path, section_cluster_map
                ),
            )
            for record in sorted(plan.unpacketizable, key=lambda r: r.record_id)
        )
        return RepairPlanV1(
            candidate_sha256=plan.candidate_sha256,
            plan_hash=plan.plan_hash,
            round_number=current_round,
            max_repair_rounds=max_repair_rounds,
            repair_permitted=repair_permitted,
            requires_deterministic_remediation=True,
            targets=targets,
        )

    problem_ids = sorted(
        set(aggregate.invalid_packet_ids)
        | set(aggregate.rejected_packet_ids)
        | set(aggregate.conflicting_packet_ids)
    )
    target_list: list[RepairTargetV1] = []
    for packet_id in problem_ids:
        packet = _find_packet(plan, packet_id)
        if packet is None:
            continue
        result = results.get(packet_id)
        if result is not None and result.failed_criteria:
            issue = "; ".join(result.failed_criteria)
        elif result is not None:
            issue = result.reasoning
        else:
            issue = "packet result is missing or failed structural validation"
        target_list.append(
            RepairTargetV1(
                packet_id=packet.packet_id,
                facet=packet.facet,
                section_path=packet.section_path,
                char_start=packet.char_start,
                char_end=packet.char_end,
                claim_ids=packet.claim_ids if isinstance(packet, BoundedFactualPacketV1) else (),
                fact_ids=(
                    packet.accepted_fact_ids if isinstance(packet, BoundedFactualPacketV1) else ()
                ),
                issue_summary=issue,
                required_section_authoring_clusters=_cluster_for(
                    packet.section_path, section_cluster_map
                ),
            )
        )
    return RepairPlanV1(
        candidate_sha256=plan.candidate_sha256,
        plan_hash=plan.plan_hash,
        round_number=current_round,
        max_repair_rounds=max_repair_rounds,
        repair_permitted=repair_permitted,
        requires_deterministic_remediation=False,
        targets=tuple(target_list),
    )


# --------------------------------------------------------------------------------------------
# Cache identity
# --------------------------------------------------------------------------------------------


def packet_cache_key(
    packet: BoundedPacketV1,
    *,
    model: str,
    schema_sha256: str,
    facts_hash: str,
    provenance_hash: str,
    sampling_parameters: Mapping[str, Any] | None = None,
) -> str:
    """Deterministic cache identity for one packet's reviewer call.

    ``packet.packet_sha256`` already embeds ``_ALGORITHM_CONTRACT_VERSION``, so an algorithm
    change invalidates through the key without needing a separate version field here.
    """

    return _canonical_hash(
        {
            "packet_id": packet.packet_id,
            "packet_sha256": packet.packet_sha256,
            "facet": packet.facet,
            "model": model,
            "schema_sha256": schema_sha256,
            "facts_hash": facts_hash,
            "provenance_hash": provenance_hash,
            "sampling_parameters": dict(sampling_parameters or {}),
        }
    )


def is_reusable_cache_entry(result: BoundedPacketResultV1) -> bool:
    """False for SYSTEM_FAILURE (never let a failure masquerade as a cached ACCEPT)."""

    return result.verdict != "SYSTEM_FAILURE"


def invalidated_packet_ids(
    old_plan: BoundedReviewPlanV1,
    new_plan: BoundedReviewPlanV1,
) -> frozenset[str]:
    """Packets whose cached result must not be reused between ``old_plan`` and ``new_plan``.

    Matches by ``stable_slot_id`` (content-hash-independent). A slot whose ``packet_sha256``
    changed, or that is new/removed, is invalidated. A visitor slot additionally invalidates its
    immediate section-order neighbors, since their neighbor-context text is now stale even though
    their own primary content did not change.
    """

    old_all: tuple[BoundedPacketV1, ...] = (*old_plan.factual_packets, *old_plan.visitor_packets)
    new_all: tuple[BoundedPacketV1, ...] = (*new_plan.factual_packets, *new_plan.visitor_packets)
    old_slots = {p.stable_slot_id: p for p in old_all}
    new_slots = {p.stable_slot_id: p for p in new_all}
    invalidated: set[str] = set()
    for slot in set(old_slots) | set(new_slots):
        old_packet = old_slots.get(slot)
        new_packet = new_slots.get(slot)
        changed = (
            old_packet is None
            or new_packet is None
            or old_packet.packet_sha256 != new_packet.packet_sha256
        )
        if changed:
            if old_packet is not None:
                invalidated.add(old_packet.packet_id)
            if new_packet is not None:
                invalidated.add(new_packet.packet_id)

    new_visitor_by_order = sorted(new_plan.visitor_packets, key=lambda p: p.order)
    section_sequence = [p.section_path for p in new_visitor_by_order]
    changed_sections = {p.section_path for p in new_visitor_by_order if p.packet_id in invalidated}
    for section in changed_sections:
        idx = section_sequence.index(section)
        for neighbor_idx in (idx - 1, idx + 1):
            if 0 <= neighbor_idx < len(section_sequence):
                invalidated.add(new_visitor_by_order[neighbor_idx].packet_id)
    return frozenset(invalidated)
