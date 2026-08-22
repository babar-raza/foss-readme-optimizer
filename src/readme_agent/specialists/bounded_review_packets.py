"""Deterministic bounded-review planning seam and compatibility exports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_accountability_models import ReadmeClaimAccountabilityMapV1
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    ReadmeDocumentPlanV1,
)
from readme_agent.specialists.bounded_review_accountability import (
    _attach_claim_ids,
    _attach_provenance_ids,
    _byte_offset_table,
    _char_span_from_byte_span,
    _claim_char_spans,
    _classify_sections,
    _dedupe_section_paths,
    _group_into_sections,
    _merge_units_for_claim_spans,
    _order_invariant_claim_accountability_hash,
    _provenance_char_spans,
    _section_path_at,
    _valid_claims_and_gaps,
    _valid_provenance_and_gaps,
    build_atomic_units,
)
from readme_agent.specialists.bounded_review_contracts import (
    _ALGORITHM_CONTRACT_VERSION,
    DEFAULT_API_INVENTORY_HEADING_KEYWORDS,
    DEFAULT_API_INVENTORY_TABLE_FENCE_THRESHOLD,
    DEFAULT_NEIGHBOR_CONTEXT_CHARS,
    AggregateOverall,
    AtomicUnitV1,
    BoundedFactualPacketV1,
    BoundedPacketV1,
    BoundedPacketVerdict,
    BoundedReviewInputMismatchError,
    BoundedReviewPlanV1,
    BoundedVisitorPacketV1,
    PacketFacet,
    SectionClassificationV1,
    UnitKind,
    UnpacketizableReason,
    UnpacketizableRecordV1,
)
from readme_agent.specialists.bounded_review_coverage import (
    CoverageLedgerV1,
    CoverageOverlapV1,
    CoverageSpanV1,
    CoverageValidationV1,
    ExcludedSpanV1,
    build_coverage_ledger,
    validate_coverage_ledger,
)
from readme_agent.specialists.bounded_review_hashing import _canonical_hash, canonical_json
from readme_agent.specialists.bounded_review_packers import (
    _build_factual_packets,
    _build_visitor_packets,
)
from readme_agent.specialists.bounded_review_repairs import (
    RepairPlanV1,
    RepairTargetV1,
    invalidated_packet_ids,
    is_reusable_cache_entry,
    packet_cache_key,
    route_selective_repairs,
)
from readme_agent.specialists.bounded_review_results import (
    AggregateVerdictV1,
    BoundedPacketResultV1,
    PacketResultValidationV1,
    aggregate_packet_results,
    validate_packet_result,
)
from readme_agent.specialists.bounded_review_structure import _build_raw_units


def plan_bounded_review_packets(
    *,
    candidate_text: str,
    document_plan: ReadmeDocumentPlanV1,
    claim_accountability: ReadmeClaimAccountabilityMapV1,
    product_facts: ProductFactsV2,
    budget_chars: int,
    factual_prompt_sha256: str,
    visitor_prompt_sha256: str,
    do_not_claim: Sequence[Mapping[str, Any]] = (),
    candidate_content_provenance: Sequence[CandidateContentProvenanceV1] = (),
    neighbor_context_chars: int = DEFAULT_NEIGHBOR_CONTEXT_CHARS,
    api_inventory_heading_keywords: frozenset[str] = DEFAULT_API_INVENTORY_HEADING_KEYWORDS,
    api_inventory_table_fence_threshold: float = DEFAULT_API_INVENTORY_TABLE_FENCE_THRESHOLD,
) -> BoundedReviewPlanV1:
    """Deterministically plan bounded review packets for one candidate.

    Raises ``BoundedReviewInputMismatchError`` on a candidate/facts/plan hash mismatch (a caller
    contract violation). A localized unresolved fact reference on one claim or provenance entry
    never raises -- it becomes an ``UnpacketizableRecordV1`` in the returned plan's
    ``unpacketizable`` list (redesign point 4).
    """

    if budget_chars <= 0:
        raise BoundedReviewInputMismatchError("budget_chars must be positive")

    candidate_sha256 = sha256_hex(candidate_text)
    if candidate_sha256 != document_plan.candidate_sha256:
        raise BoundedReviewInputMismatchError(
            "candidate_text sha256 does not match document_plan.candidate_sha256"
        )
    if candidate_sha256 != claim_accountability.candidate_sha256:
        raise BoundedReviewInputMismatchError(
            "candidate_text sha256 does not match claim_accountability.candidate_sha256"
        )
    facts_hash = product_facts.canonical_hash()
    if document_plan.facts_hash != facts_hash:
        raise BoundedReviewInputMismatchError(
            "document_plan.facts_hash does not match product_facts.canonical_hash()"
        )
    if claim_accountability.facts_hash != facts_hash:
        raise BoundedReviewInputMismatchError(
            "claim_accountability.facts_hash does not match product_facts.canonical_hash()"
        )

    input_contract_hash = sha256_hex(_ALGORITHM_CONTRACT_VERSION)

    valid_claims, claim_gaps = _valid_claims_and_gaps(claim_accountability, product_facts)
    valid_provenance, provenance_gaps = _valid_provenance_and_gaps(
        candidate_content_provenance, product_facts
    )

    raw_units = _build_raw_units(candidate_text)
    byte_offsets = _byte_offset_table(candidate_text)

    unpacketizable: list[UnpacketizableRecordV1] = []
    for claim, missing_fact_id in claim_gaps:
        char_start, char_end = _char_span_from_byte_span(
            byte_offsets, claim.source_byte_start, claim.source_byte_end
        )
        unpacketizable.append(
            UnpacketizableRecordV1(
                record_id=f"unpacketizable-claim-{claim.claim_id}",
                reason="unresolved_fact_reference",
                section_path=_section_path_at(raw_units, char_start),
                char_start=char_start,
                char_end=char_end if char_end > char_start else char_start + 1,
                claim_id=claim.claim_id,
                missing_fact_id=missing_fact_id,
                detail=(
                    f"claim {claim.claim_id!r} cites unresolved fact id {missing_fact_id!r} not "
                    "present in product_facts"
                ),
            )
        )
    for entry, missing_fact_id in provenance_gaps:
        char_start, char_end = _char_span_from_byte_span(
            byte_offsets, entry.candidate_byte_start, entry.candidate_byte_end
        )
        unpacketizable.append(
            UnpacketizableRecordV1(
                record_id=f"unpacketizable-provenance-{entry.provenance_id}",
                reason="unresolved_fact_reference",
                section_path=_section_path_at(raw_units, char_start),
                char_start=char_start,
                char_end=char_end if char_end > char_start else char_start + 1,
                provenance_id=entry.provenance_id,
                missing_fact_id=missing_fact_id,
                detail=(
                    f"provenance {entry.provenance_id!r} cites unresolved fact id "
                    f"{missing_fact_id!r} not present in product_facts"
                ),
            )
        )

    claim_char_spans = _claim_char_spans(byte_offsets, valid_claims)
    merged_units = _merge_units_for_claim_spans(raw_units, claim_char_spans)
    _attach_claim_ids(merged_units, claim_char_spans)
    all_provenance_spans = _provenance_char_spans(byte_offsets, candidate_content_provenance)
    _attach_provenance_ids(merged_units, all_provenance_spans)
    sections = _group_into_sections(merged_units)
    _dedupe_section_paths(sections)
    for index, unit in enumerate(merged_units):
        unit.unit_id = f"unit-{index:04d}-{unit.kind}"

    section_classifications = _classify_sections(
        sections,
        api_inventory_heading_keywords=api_inventory_heading_keywords,
        api_inventory_table_fence_threshold=api_inventory_table_fence_threshold,
    )

    accepted_fact_ids_by_claim = {
        claim.claim_id: tuple(claim.accepted_fact_ids) for claim in valid_claims
    }
    valid_provenance_char_spans = {
        entry.provenance_id: _char_span_from_byte_span(
            byte_offsets, entry.candidate_byte_start, entry.candidate_byte_end
        )
        for entry in valid_provenance
    }
    do_not_claim_sorted = tuple(
        sorted(
            (dict(item) for item in do_not_claim),
            key=lambda item: str(item.get("fact_id", "")),
        )
    )

    factual_packets, factual_oversized = _build_factual_packets(
        sections=sections,
        candidate_text=candidate_text,
        candidate_sha256=candidate_sha256,
        product_facts=product_facts,
        accepted_fact_ids_by_claim=accepted_fact_ids_by_claim,
        do_not_claim_sorted=do_not_claim_sorted,
        valid_provenance=valid_provenance,
        provenance_char_spans=valid_provenance_char_spans,
        budget_chars=budget_chars,
        factual_prompt_sha256=factual_prompt_sha256,
        input_contract_hash=input_contract_hash,
        algorithm_contract_version=_ALGORITHM_CONTRACT_VERSION,
    )
    visitor_packets, visitor_oversized = _build_visitor_packets(
        sections=sections,
        section_classifications=section_classifications,
        candidate_text=candidate_text,
        candidate_sha256=candidate_sha256,
        budget_chars=budget_chars,
        neighbor_context_chars=neighbor_context_chars,
        visitor_prompt_sha256=visitor_prompt_sha256,
        input_contract_hash=input_contract_hash,
        algorithm_contract_version=_ALGORITHM_CONTRACT_VERSION,
    )
    unpacketizable.extend(factual_oversized)
    unpacketizable.extend(visitor_oversized)
    unpacketizable.sort(key=lambda record: record.record_id)

    plan_hash = _canonical_hash(
        {
            "algorithm_contract_version": _ALGORITHM_CONTRACT_VERSION,
            "candidate_sha256": candidate_sha256,
            "document_plan_candidate_sha256": document_plan.candidate_sha256,
            "facts_hash": facts_hash,
            "claim_accountability_hash": _order_invariant_claim_accountability_hash(
                claim_accountability
            ),
            "budget_chars": budget_chars,
            "neighbor_context_chars": neighbor_context_chars,
        }
    )

    return BoundedReviewPlanV1(
        candidate_sha256=candidate_sha256,
        plan_hash=plan_hash,
        budget_chars=budget_chars,
        factual_packets=tuple(factual_packets),
        visitor_packets=tuple(visitor_packets),
        unpacketizable=tuple(unpacketizable),
    )


__all__ = [
    "DEFAULT_API_INVENTORY_HEADING_KEYWORDS",
    "DEFAULT_API_INVENTORY_TABLE_FENCE_THRESHOLD",
    "DEFAULT_NEIGHBOR_CONTEXT_CHARS",
    "AggregateOverall",
    "AggregateVerdictV1",
    "AtomicUnitV1",
    "BoundedFactualPacketV1",
    "BoundedPacketResultV1",
    "BoundedPacketV1",
    "BoundedPacketVerdict",
    "BoundedReviewInputMismatchError",
    "BoundedReviewPlanV1",
    "BoundedVisitorPacketV1",
    "CoverageLedgerV1",
    "CoverageOverlapV1",
    "CoverageSpanV1",
    "CoverageValidationV1",
    "ExcludedSpanV1",
    "PacketFacet",
    "PacketResultValidationV1",
    "RepairPlanV1",
    "RepairTargetV1",
    "SectionClassificationV1",
    "UnitKind",
    "UnpacketizableReason",
    "UnpacketizableRecordV1",
    "aggregate_packet_results",
    "build_atomic_units",
    "build_coverage_ledger",
    "canonical_json",
    "invalidated_packet_ids",
    "is_reusable_cache_entry",
    "packet_cache_key",
    "plan_bounded_review_packets",
    "route_selective_repairs",
    "validate_coverage_ledger",
    "validate_packet_result",
]
