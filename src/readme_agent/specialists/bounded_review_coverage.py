"""Coverage ledger construction and validation for bounded README review."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import Field, model_validator

from readme_agent.specialists.bounded_review_accountability import (
    _classify_sections,
    _group_into_sections,
)
from readme_agent.specialists.bounded_review_contracts import (
    _SHA256_PATTERN,
    DEFAULT_API_INVENTORY_HEADING_KEYWORDS,
    DEFAULT_API_INVENTORY_TABLE_FENCE_THRESHOLD,
    AtomicUnitV1,
    BoundedPacketV1,
    BoundedReviewPlanV1,
    UnitKind,
    _StrictModel,
)
from readme_agent.specialists.bounded_review_hashing import _canonical_hash


class CoverageSpanV1(_StrictModel):
    """One atomic unit's assignment to zero or more covering packets for one facet."""

    unit_id: str = Field(min_length=1)
    section_path: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    unit_kind: UnitKind
    covering_packet_ids: tuple[str, ...] = ()


class ExcludedSpanV1(_StrictModel):
    """One atomic unit explicitly excluded from visitor coverage, with its justification."""

    unit_id: str = Field(min_length=1)
    section_path: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    classification: str = Field(min_length=1)
    justification: str = Field(min_length=1)


class CoverageOverlapV1(_StrictModel):
    """One intentional multi-packet coverage of the same subject (e.g. neighbor-context text)."""

    subject: str = Field(min_length=1)
    packet_ids: tuple[str, ...]
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def _at_least_two_packets(self) -> CoverageOverlapV1:
        if len(self.packet_ids) < 2:
            raise ValueError("a coverage overlap requires at least two covering packets")
        return self


class CoverageLedgerV1(_StrictModel):
    """Proof that every required span is covered, bound to exact candidate/plan hashes."""

    schema_version: Literal[1] = 1
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_hash: str = Field(pattern=_SHA256_PATTERN)
    visitor_spans: tuple[CoverageSpanV1, ...] = ()
    factual_spans: tuple[CoverageSpanV1, ...] = ()
    excluded_spans: tuple[ExcludedSpanV1, ...] = ()
    overlaps: tuple[CoverageOverlapV1, ...] = ()
    blocking_record_ids: tuple[str, ...] = ()

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


class CoverageValidationV1(_StrictModel):
    """Structural completeness of one coverage ledger.

    ``is_complete`` and ``has_blocking_gaps`` are deliberately independent (redesign point 5):
    a ledger can be complete (every span assigned) yet still ``has_blocking_gaps`` when the bound
    plan carries unpacketizable records, and that is exactly what drives the ``BLOCKED`` aggregate
    state below, distinct from ``INCOMPLETE``.
    """

    is_complete: bool
    has_blocking_gaps: bool
    unassigned_visitor_span_ids: tuple[str, ...] = ()
    unassigned_factual_span_ids: tuple[str, ...] = ()


def validate_coverage_ledger(ledger: CoverageLedgerV1) -> CoverageValidationV1:
    """Never raises; reports completeness and blocking-gap status independently."""

    unassigned_visitor = tuple(
        sorted(span.unit_id for span in ledger.visitor_spans if not span.covering_packet_ids)
    )
    unassigned_factual = tuple(
        sorted(span.unit_id for span in ledger.factual_spans if not span.covering_packet_ids)
    )
    return CoverageValidationV1(
        is_complete=not unassigned_visitor and not unassigned_factual,
        has_blocking_gaps=bool(ledger.blocking_record_ids),
        unassigned_visitor_span_ids=unassigned_visitor,
        unassigned_factual_span_ids=unassigned_factual,
    )


def build_coverage_ledger(
    plan: BoundedReviewPlanV1,
    *,
    atomic_units: Sequence[AtomicUnitV1],
    api_inventory_heading_keywords: frozenset[str] = DEFAULT_API_INVENTORY_HEADING_KEYWORDS,
    api_inventory_table_fence_threshold: float = DEFAULT_API_INVENTORY_TABLE_FENCE_THRESHOLD,
) -> CoverageLedgerV1:
    """Prove exhaustive coverage for one plan against its own ``atomic_units``.

    Pass the same ``api_inventory_heading_keywords``/``api_inventory_table_fence_threshold`` used
    to build ``plan`` -- this function recomputes section classification from ``atomic_units``
    rather than reading it back off the plan, since ``BoundedReviewPlanV1`` does not carry
    classification directly (only ``visitor_packets`` absence for excluded sections).
    """

    sections = _group_into_sections(list(atomic_units))
    classifications = _classify_sections(
        sections,
        api_inventory_heading_keywords=api_inventory_heading_keywords,
        api_inventory_table_fence_threshold=api_inventory_table_fence_threshold,
    )

    factual_covering: dict[str, list[str]] = {
        unit.unit_id: [] for unit in atomic_units if unit.requires_factual_review
    }
    for factual_packet in plan.factual_packets:
        for unit_id in factual_packet.covered_unit_ids:
            if unit_id in factual_covering:
                factual_covering[unit_id].append(factual_packet.packet_id)

    visitor_covering: dict[str, list[str]] = {}
    excluded_spans: list[ExcludedSpanV1] = []
    for unit in atomic_units:
        classification = classifications[unit.section_path]
        if classification.classification == "mechanical_api_inventory":
            excluded_spans.append(
                ExcludedSpanV1(
                    unit_id=unit.unit_id,
                    section_path=unit.section_path,
                    char_start=unit.char_start,
                    char_end=unit.char_end,
                    classification="mechanical_api_inventory",
                    justification=classification.justification,
                )
            )
        else:
            visitor_covering[unit.unit_id] = []
    for visitor_packet_item in plan.visitor_packets:
        for unit_id in visitor_packet_item.covered_unit_ids:
            if unit_id in visitor_covering:
                visitor_covering[unit_id].append(visitor_packet_item.packet_id)

    unit_by_id = {unit.unit_id: unit for unit in atomic_units}
    all_packets: tuple[BoundedPacketV1, ...] = (*plan.factual_packets, *plan.visitor_packets)
    packet_spans = {
        packet.packet_id: (packet.char_start, packet.char_end) for packet in all_packets
    }

    def retain_only_complete_coverage(mapping: dict[str, list[str]]) -> None:
        """Require the cited packet-span union to cover every byte of its atomic unit."""

        for unit_id, packet_ids in mapping.items():
            unit = unit_by_id[unit_id]
            cursor = unit.char_start
            for start, end in sorted(
                (
                    (
                        max(unit.char_start, packet_spans[packet_id][0]),
                        min(unit.char_end, packet_spans[packet_id][1]),
                    )
                    for packet_id in packet_ids
                ),
            ):
                if end <= cursor:
                    continue
                if start > cursor:
                    break
                cursor = max(cursor, end)
                if cursor >= unit.char_end:
                    break
            if cursor < unit.char_end:
                mapping[unit_id] = []

    retain_only_complete_coverage(factual_covering)
    retain_only_complete_coverage(visitor_covering)
    visitor_spans = tuple(
        CoverageSpanV1(
            unit_id=unit_id,
            section_path=unit_by_id[unit_id].section_path,
            char_start=unit_by_id[unit_id].char_start,
            char_end=unit_by_id[unit_id].char_end,
            unit_kind=unit_by_id[unit_id].kind,
            covering_packet_ids=tuple(sorted(packet_ids)),
        )
        for unit_id, packet_ids in sorted(visitor_covering.items())
    )
    factual_spans = tuple(
        CoverageSpanV1(
            unit_id=unit_id,
            section_path=unit_by_id[unit_id].section_path,
            char_start=unit_by_id[unit_id].char_start,
            char_end=unit_by_id[unit_id].char_end,
            unit_kind=unit_by_id[unit_id].kind,
            covering_packet_ids=tuple(sorted(packet_ids)),
        )
        for unit_id, packet_ids in sorted(factual_covering.items())
    )

    overlaps: list[CoverageOverlapV1] = []
    visitor_by_order = sorted(plan.visitor_packets, key=lambda packet: packet.order)
    for index in range(1, len(visitor_by_order)):
        prev_packet = visitor_by_order[index - 1]
        current_packet = visitor_by_order[index]
        if current_packet.neighbor_context_before:
            overlaps.append(
                CoverageOverlapV1(
                    subject=(
                        f"visitor-neighbor-context:{prev_packet.section_path}"
                        f"->{current_packet.section_path}"
                    ),
                    packet_ids=(prev_packet.packet_id, current_packet.packet_id),
                    reason=(
                        "neighbor context intentionally duplicates the adjacent packet's own "
                        "prose for flow continuity"
                    ),
                )
            )

    return CoverageLedgerV1(
        candidate_sha256=plan.candidate_sha256,
        plan_hash=plan.plan_hash,
        visitor_spans=visitor_spans,
        factual_spans=factual_spans,
        excluded_spans=tuple(excluded_spans),
        overlaps=tuple(overlaps),
        blocking_record_ids=tuple(sorted(record.record_id for record in plan.unpacketizable)),
    )
