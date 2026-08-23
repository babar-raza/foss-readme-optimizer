"""Tests for the standalone bounded-review packetizer, validator, aggregator, and repair router.

Builds minimal-but-valid ``ReadmeDocumentPlanV1`` / ``ReadmeClaimAccountabilityMapV1`` /
``ProductFactsV2`` instances with a private helper below (no new support module -- outside the
granted writable test scope) against the synthetic ~162KB candidate at
``tests/fixtures/bounded_review_packets/candidate.md``. Claim/provenance spans are located by
searching for exact literal marker sentences in the loaded fixture text at test time, never by
hardcoded byte offsets, so the fixture can be edited without hand-recomputing spans as long as the
markers are preserved.
"""

from __future__ import annotations

import pytest
from bounded_review_test_support import (
    CANDIDATE_TEXT,
    DEFAULT_DOCUMENT_PLAN,
    DEFAULT_FACTS,
    DEFAULT_PROVENANCE,
    _accept_result_for,
    _all_accept_results,
    _all_required_packets,
    _atomic_units,
    _build_claim_accountability,
    _ClaimSpec,
    _default_claim_specs,
    _plan,
    _reject_result_for,
)

from readme_agent.specialists import bounded_review_packets as brp
from readme_agent.specialists.review_finding_grounding import GroundedReviewFindingV1


def test_missing_packet_result_yields_incomplete_never_accept() -> None:
    plan = _plan()
    units = _atomic_units()
    ledger = brp.build_coverage_ledger(plan, atomic_units=units)
    all_packets = _all_required_packets(plan)
    dropped = all_packets[0]
    results = _all_accept_results(plan)
    del results[dropped.packet_id]

    aggregate = brp.aggregate_packet_results(plan, ledger, results)
    assert aggregate.overall == "INCOMPLETE"
    assert dropped.packet_id in aggregate.missing_packet_ids


# --------------------------------------------------------------------------------------------
# 14. Stale candidate hash fails closed
# --------------------------------------------------------------------------------------------


def test_stale_candidate_hash_in_result_fails_closed() -> None:
    plan = _plan()
    packet = plan.visitor_packets[0]
    result = _accept_result_for(packet).model_copy(update={"candidate_sha256": "0" * 64})
    validation = brp.validate_packet_result(plan, result)
    assert validation.valid is False
    assert any("candidate_sha256" in error for error in validation.errors)


# --------------------------------------------------------------------------------------------
# 15. Context overlap is non-authoritative; authoritative overlap may conflict
# --------------------------------------------------------------------------------------------


def test_neighbor_context_disagreement_routes_repair_instead_of_conflict() -> None:
    plan = _plan()
    units = _atomic_units()
    ledger = brp.build_coverage_ledger(plan, atomic_units=units)
    assert ledger.overlaps, "expected at least one visitor neighbor-context overlap"

    overlap = ledger.overlaps[0]
    packets_by_id = {p.packet_id: p for p in _all_required_packets(plan)}
    rejected_id = overlap.packet_ids[1]
    results = _all_accept_results(
        plan, overrides={rejected_id: _reject_result_for(packets_by_id[rejected_id])}
    )

    aggregate = brp.aggregate_packet_results(plan, ledger, results)
    assert aggregate.overall == "REJECTED"
    assert aggregate.rejected_packet_ids == (rejected_id,)


def test_conflicting_authoritative_overlap_yields_conflict() -> None:
    plan = _plan()
    units = _atomic_units()
    ledger = brp.build_coverage_ledger(plan, atomic_units=units)
    packets = list(plan.visitor_packets[:2])
    authoritative_overlap = brp.CoverageOverlapV1(
        subject="authoritative-target-overlap:synthetic",
        packet_ids=(packets[0].packet_id, packets[1].packet_id),
        reason="synthetic authoritative overlap for reducer coverage",
    )
    ledger = ledger.model_copy(update={"overlaps": (*ledger.overlaps, authoritative_overlap)})
    results = _all_accept_results(
        plan,
        overrides={packets[1].packet_id: _reject_result_for(packets[1])},
    )

    aggregate = brp.aggregate_packet_results(plan, ledger, results)
    assert aggregate.overall == "CONFLICT"
    assert set(authoritative_overlap.packet_ids) <= set(aggregate.conflicting_packet_ids)


# --------------------------------------------------------------------------------------------
# 16. Finding referencing outside its packet fails closed
# --------------------------------------------------------------------------------------------


def test_finding_referencing_span_outside_packet_fails_closed() -> None:
    plan = _plan()
    packet = plan.visitor_packets[0]
    finding = GroundedReviewFindingV1(
        finding_id="finding.out.of.span",
        kind="quality",
        criterion="clarity",
        section=packet.section_path,
        claim="Claims something about text this packet does not contain.",
        quoted_candidate_span="This exact sentence does not occur anywhere in this packet.",
        disposition="supports_acceptance",
        polarity_result="not_applicable",
    )
    result = brp.BoundedPacketResultV1(
        packet_id=packet.packet_id,
        facet=packet.facet,
        candidate_sha256=packet.candidate_sha256,
        packet_sha256=packet.packet_sha256,
        prompt_contract_hash=packet.prompt_contract_hash,
        input_contract_hash=packet.input_contract_hash,
        verdict="ACCEPT",
        reasoning="Synthetic accept referencing an out-of-span quote.",
        findings=(finding,),
    )
    validation = brp.validate_packet_result(plan, result)
    assert validation.valid is False
    assert any("outside" in error for error in validation.errors)


# --------------------------------------------------------------------------------------------
# 17. Referential gap vs contract violation
# --------------------------------------------------------------------------------------------


def test_referential_gap_is_localized_not_a_crash() -> None:
    specs = _default_claim_specs()
    broken_specs = [
        _ClaimSpec(spec.claim_id, spec.marker, "nonexistent.fact:primary", spec.marker_end)
        if spec.claim_id == "claim-overview-problem"
        else spec
        for spec in specs
    ]
    broken_claims = _build_claim_accountability(CANDIDATE_TEXT, DEFAULT_FACTS, broken_specs)

    plan = _plan(claim_accountability=broken_claims)
    assert plan.unpacketizable
    gap_records = [
        record for record in plan.unpacketizable if record.reason == "unresolved_fact_reference"
    ]
    assert any(record.claim_id == "claim-overview-problem" for record in gap_records)
    assert all(record.missing_fact_id == "nonexistent.fact:primary" for record in gap_records)


def test_contract_violation_raises_on_hash_mismatch() -> None:
    mismatched_document_plan = DEFAULT_DOCUMENT_PLAN.model_copy(
        update={"candidate_sha256": "0" * 64}
    )
    with pytest.raises(brp.BoundedReviewInputMismatchError):
        _plan(document_plan=mismatched_document_plan)


# --------------------------------------------------------------------------------------------
# 18. BLOCKED vs INCOMPLETE
# --------------------------------------------------------------------------------------------


def test_blocked_differs_from_incomplete_and_routes_deterministic_remediation() -> None:
    specs = _default_claim_specs()
    broken_specs = [
        _ClaimSpec(spec.claim_id, spec.marker, "nonexistent.fact:primary", spec.marker_end)
        if spec.claim_id == "claim-overview-problem"
        else spec
        for spec in specs
    ]
    broken_claims = _build_claim_accountability(CANDIDATE_TEXT, DEFAULT_FACTS, broken_specs)
    plan = _plan(claim_accountability=broken_claims)
    assert plan.unpacketizable

    units = brp.build_atomic_units(CANDIDATE_TEXT, broken_claims, DEFAULT_FACTS, DEFAULT_PROVENANCE)
    ledger = brp.build_coverage_ledger(plan, atomic_units=units)
    results = _all_accept_results(plan)

    aggregate = brp.aggregate_packet_results(plan, ledger, results)
    assert aggregate.overall == "BLOCKED"
    assert set(aggregate.blocking_record_ids) == {r.record_id for r in plan.unpacketizable}

    repair_plan = brp.route_selective_repairs(
        plan, aggregate, results, current_round=0, max_repair_rounds=2
    )
    assert repair_plan.requires_deterministic_remediation is True
    assert len(repair_plan.targets) == len(plan.unpacketizable)
    assert all(target.packet_id is None for target in repair_plan.targets)


# --------------------------------------------------------------------------------------------
# 19. One failed packet -> narrow repair target
# --------------------------------------------------------------------------------------------


def test_one_failed_packet_yields_a_narrow_repair_target() -> None:
    plan = _plan()
    units = _atomic_units()
    ledger = brp.build_coverage_ledger(plan, atomic_units=units)
    failing_packet = plan.factual_packets[0]
    results = _all_accept_results(
        plan, overrides={failing_packet.packet_id: _reject_result_for(failing_packet)}
    )

    aggregate = brp.aggregate_packet_results(plan, ledger, results)
    assert aggregate.overall == "REJECTED"
    assert aggregate.rejected_packet_ids == (failing_packet.packet_id,)

    repair_plan = brp.route_selective_repairs(
        plan, aggregate, results, current_round=0, max_repair_rounds=2
    )
    assert repair_plan.requires_deterministic_remediation is False
    assert len(repair_plan.targets) == 1
    assert repair_plan.targets[0].packet_id == failing_packet.packet_id
    total_packets = len(plan.factual_packets) + len(plan.visitor_packets)
    assert len(repair_plan.targets) < total_packets


# --------------------------------------------------------------------------------------------
# 20. max_repair_rounds represented but never autonomously exceeded
# --------------------------------------------------------------------------------------------


def test_max_repair_rounds_represented_but_not_autonomously_exceeded() -> None:
    plan = _plan()
    units = _atomic_units()
    ledger = brp.build_coverage_ledger(plan, atomic_units=units)
    results = _all_accept_results(plan)
    aggregate = brp.aggregate_packet_results(plan, ledger, results)
    assert aggregate.overall == "ACCEPT"

    within_bound = brp.route_selective_repairs(
        plan, aggregate, results, current_round=1, max_repair_rounds=2
    )
    at_bound = brp.route_selective_repairs(
        plan, aggregate, results, current_round=2, max_repair_rounds=2
    )
    assert within_bound.repair_permitted is True
    assert at_bound.repair_permitted is False
    # An ACCEPT aggregate has no problem packets, so the target set is empty regardless of
    # round -- the bound only governs whether a caller may issue another round, never whether
    # this module issues one itself (it never does; see test_module_never_calls_a_provider).
    assert within_bound.targets == ()
    assert at_bound.targets == ()


# --------------------------------------------------------------------------------------------
# 21. Same complete result set aggregated twice -> byte-identical output
# --------------------------------------------------------------------------------------------


def test_same_result_set_aggregated_twice_is_byte_identical() -> None:
    plan = _plan()
    units = _atomic_units()
    ledger = brp.build_coverage_ledger(plan, atomic_units=units)
    results = _all_accept_results(plan)

    aggregate_a = brp.aggregate_packet_results(plan, ledger, results)
    aggregate_b = brp.aggregate_packet_results(plan, ledger, results)
    assert brp.canonical_json(aggregate_a) == brp.canonical_json(aggregate_b)
    assert aggregate_a.overall == "ACCEPT"
