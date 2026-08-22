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
    DEFAULT_FACTS,
    _all_required_packets,
    _atomic_units,
    _build_claim_accountability,
    _build_document_plan,
    _build_product_facts,
    _default_claim_specs,
    _default_provenance,
    _plan,
)

from readme_agent.specialists import bounded_review_packets as brp


def test_full_visitor_and_factual_coverage() -> None:
    plan = _plan()
    units = _atomic_units()
    ledger = brp.build_coverage_ledger(plan, atomic_units=units)
    validation = brp.validate_coverage_ledger(ledger)
    assert validation.is_complete is True
    assert validation.unassigned_visitor_span_ids == ()
    assert validation.unassigned_factual_span_ids == ()
    assert ledger.visitor_spans
    assert ledger.factual_spans


# --------------------------------------------------------------------------------------------
# 9. API-inventory exclusion
# --------------------------------------------------------------------------------------------


def test_api_inventory_section_excluded_from_visitor_included_in_factual() -> None:
    plan = _plan()
    units = _atomic_units()
    ledger = brp.build_coverage_ledger(plan, atomic_units=units)

    assert ledger.excluded_spans
    for span in ledger.excluded_spans:
        assert span.classification == "mechanical_api_inventory"
        assert span.justification
        assert span.section_path == "api-reference"

    assert all(p.section_path != "api-reference" for p in plan.visitor_packets)
    assert any(p.section_path == "api-reference" for p in plan.factual_packets)


# --------------------------------------------------------------------------------------------
# 10. Selective invalidation on a one-section text edit
# --------------------------------------------------------------------------------------------


def test_editing_one_section_invalidates_only_that_sections_packets() -> None:
    plan_before = _plan()

    # Edit a sentence that is NOT a claim marker (every _default_claim_specs() marker must
    # remain findable verbatim in edited_text, since _build_claim_accountability locates spans
    # by exact substring search against whichever candidate_text it is given).
    edited_text = CANDIDATE_TEXT.replace(
        "It targets internal-tools teams who need a consistent set of layout, data, and form "
        "primitives without adopting a full application framework.",
        "It targets platform teams who need a consistent set of layout, data, and form "
        "primitives without adopting a full application framework.",
    )
    assert edited_text != CANDIDATE_TEXT

    edited_facts = DEFAULT_FACTS
    edited_document_plan = _build_document_plan(edited_text, edited_facts)
    edited_claims = _build_claim_accountability(edited_text, edited_facts, _default_claim_specs())
    edited_provenance = _default_provenance(edited_text)

    plan_after = _plan(
        candidate_text=edited_text,
        document_plan=edited_document_plan,
        claim_accountability=edited_claims,
        candidate_content_provenance=edited_provenance,
    )

    invalidated = brp.invalidated_packet_ids(plan_before, plan_after)
    all_ids = {p.packet_id for p in _all_required_packets(plan_before)} | {
        p.packet_id for p in _all_required_packets(plan_after)
    }
    assert invalidated
    assert invalidated < all_ids

    overview_before = {
        p.packet_id for p in plan_before.visitor_packets if p.section_path == "overview"
    }
    license_before = {
        p.packet_id for p in plan_before.visitor_packets if p.section_path == "license"
    }
    assert overview_before & invalidated
    assert not (license_before & invalidated)


# --------------------------------------------------------------------------------------------
# 11. Fact change invalidates only affected factual packets
# --------------------------------------------------------------------------------------------


def test_fact_change_invalidates_only_affected_factual_packets() -> None:
    plan_before = _plan()

    updated_facts = _build_product_facts(
        overrides={"product.limitations": "Updated: only nested row grouping remains missing."}
    )
    updated_document_plan = _build_document_plan(CANDIDATE_TEXT, updated_facts)
    updated_claims = _build_claim_accountability(
        CANDIDATE_TEXT, updated_facts, _default_claim_specs()
    )
    plan_after = _plan(
        document_plan=updated_document_plan,
        claim_accountability=updated_claims,
        product_facts=updated_facts,
    )

    invalidated = brp.invalidated_packet_ids(plan_before, plan_after)

    before_visitor_ids = {p.packet_id for p in plan_before.visitor_packets}
    after_visitor_ids = {p.packet_id for p in plan_after.visitor_packets}
    assert before_visitor_ids == after_visitor_ids
    assert not (before_visitor_ids & invalidated)

    limitations_before = {
        p.packet_id
        for p in plan_before.factual_packets
        if p.section_path == "scope-and-limitations"
    }
    assert limitations_before & invalidated

    license_before = {
        p.packet_id for p in plan_before.factual_packets if p.section_path == "license"
    }
    license_after = {p.packet_id for p in plan_after.factual_packets if p.section_path == "license"}
    assert license_before == license_after
    assert not (license_before & invalidated)


# --------------------------------------------------------------------------------------------
# 12. Algorithm-version change invalidates every packet_sha256
# --------------------------------------------------------------------------------------------


def test_algorithm_contract_version_change_changes_every_packet_sha256(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan_before = _plan()
    monkeypatch.setattr(brp, "_ALGORITHM_CONTRACT_VERSION", "bounded-review-packets-v1-test-bump")
    plan_after = _plan()

    assert plan_before.plan_hash != plan_after.plan_hash
    before_by_slot = {p.stable_slot_id: p.packet_sha256 for p in _all_required_packets(plan_before)}
    after_by_slot = {p.stable_slot_id: p.packet_sha256 for p in _all_required_packets(plan_after)}
    assert set(before_by_slot) == set(after_by_slot)
    for slot, before_hash in before_by_slot.items():
        assert after_by_slot[slot] != before_hash
