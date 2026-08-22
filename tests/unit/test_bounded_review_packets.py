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

import json

import pytest
from bounded_review_test_support import (
    CANDIDATE_TEXT,
    DEFAULT_CLAIM_ACCOUNTABILITY,
    DEFAULT_DO_NOT_CLAIM,
    DEFAULT_DOCUMENT_PLAN,
    DEFAULT_FACTS,
    DEFAULT_PROVENANCE,
    FIXTURE_DIR,
    _atomic_units,
    _build_claim_accountability,
    _claim_span,
    _default_claim_specs,
    _FailIfCalledClient,
    _PacketSequenceClient,
    _plan,
)

from readme_agent.presentation.visitor_contract import build_presentation_visitor_contract
from readme_agent.specialists import bounded_review_packets as brp
from readme_agent.specialists import separated_readme_review as separated_review
from readme_agent.specialists.bounded_review_execution import execute_bounded_review


def test_synthetic_candidate_plans_successfully_within_budget() -> None:
    assert 100_000 <= len(CANDIDATE_TEXT.encode("utf-8")) <= 250_000
    plan = _plan()
    assert plan.factual_packets
    assert plan.visitor_packets
    for packet in plan.visitor_packets:
        assert packet.char_end - packet.char_start <= plan.budget_chars
    for packet in plan.factual_packets:
        facts_json = json.dumps(
            list(packet.facts), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        size = (packet.char_end - packet.char_start) + len(facts_json)
        assert size <= plan.budget_chars


def test_real_candidate_accountability_selects_current_claims_without_survival_flag() -> None:
    """The production claim builder leaves candidate survival unset by design."""

    claims = [
        claim.model_copy(update={"survives_in_candidate": None})
        for claim in DEFAULT_CLAIM_ACCOUNTABILITY.claims
    ]
    accountability = DEFAULT_CLAIM_ACCOUNTABILITY.model_copy(update={"claims": claims})

    plan = _plan(claim_accountability=accountability)

    covered_claim_ids = {
        claim_id for packet in plan.factual_packets for claim_id in packet.claim_ids
    }
    assert covered_claim_ids == {claim.claim_id for claim in claims}


def test_bounded_execution_reviews_every_packet_and_reduces_to_established_roles() -> None:
    plan = _plan()
    units = _atomic_units()
    ledger = brp.build_coverage_ledger(plan, atomic_units=units)
    visitor_packets = list(plan.visitor_packets)
    factual_packets = list(plan.factual_packets)
    blind_client = _PacketSequenceClient(visitor_packets)
    factual_client = _PacketSequenceClient(factual_packets)
    h2_headings = [
        line.removeprefix("## ").strip()
        for line in CANDIDATE_TEXT.splitlines()
        if line.startswith("## ")
    ]

    execution = execute_bounded_review(
        org_repo="acme/widget-toolkit",
        candidate_text=CANDIDATE_TEXT,
        product_facts=DEFAULT_FACTS.model_dump(mode="json"),
        visitor_contract=build_presentation_visitor_contract(
            applicable_h2_headings=h2_headings,
            primary_example_language="python",
        ),
        plan=plan,
        coverage_ledger=ledger,
        blind_client=blind_client,
        factual_client=factual_client,
        blind_prompt_id="blind_readme_quality_review",
        factual_prompt_id="factual_readme_plan_review",
    )

    assert execution.aggregate.overall == "ACCEPT"
    assert execution.blind_result.verdict == "ACCEPT"
    assert execution.factual_result.verdict == "ACCEPT"
    assert blind_client.calls == len(visitor_packets)
    assert factual_client.calls == len(factual_packets)
    assert len(execution.packet_results) == len(visitor_packets) + len(factual_packets)


def test_separated_review_routes_large_valid_contract_through_bounded_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_plan = DEFAULT_DOCUMENT_PLAN.model_copy(
        update={
            "claim_accountability": DEFAULT_CLAIM_ACCOUNTABILITY,
            "candidate_content_provenance": DEFAULT_PROVENANCE,
        }
    )
    plan = _plan(document_plan=document_plan, budget_chars=100_000)
    blind_client = _PacketSequenceClient(list(plan.visitor_packets))
    factual_client = _PacketSequenceClient(list(plan.factual_packets))
    monkeypatch.setattr(separated_review, "_BOUNDED_REVIEW_TRIGGER_CHARS", 1)

    review = separated_review.run_separated_readme_review(
        "acme/widget-toolkit",
        "# Widget Toolkit\n",
        CANDIDATE_TEXT,
        document_plan.model_dump(mode="json"),
        DEFAULT_FACTS.model_dump(mode="json"),
        blind_client=blind_client,
        factual_client=factual_client,
    )

    assert review.verdict == "ACCEPT"
    assert review.bounded_review_receipt is not None
    assert review.bounded_review_receipt["aggregate"]["overall"] == "ACCEPT"
    assert blind_client.calls == len(plan.visitor_packets)
    assert factual_client.calls == len(plan.factual_packets)


def test_oversized_invalid_contract_fails_closed_instead_of_using_merged_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(separated_review, "_BOUNDED_REVIEW_TRIGGER_CHARS", 1)

    with pytest.raises(RuntimeError, match="oversized review requires valid typed"):
        separated_review.run_separated_readme_review(
            "acme/widget-toolkit",
            "# Widget Toolkit\n",
            CANDIDATE_TEXT,
            {"readme_document_plan": {"schema_version": "invalid"}},
            DEFAULT_FACTS.model_dump(mode="json"),
            blind_client=_FailIfCalledClient(),
            factual_client=_FailIfCalledClient(),
        )


# --------------------------------------------------------------------------------------------
# 2. Deterministic packet order/IDs/hashes across two independent runs
# --------------------------------------------------------------------------------------------


def test_deterministic_across_two_independent_runs() -> None:
    plan_a = _plan()
    plan_b = _plan()
    assert plan_a == plan_b
    assert plan_a.canonical_hash() == plan_b.canonical_hash()
    assert [p.packet_id for p in plan_a.factual_packets] == [
        p.packet_id for p in plan_b.factual_packets
    ]
    assert [p.packet_id for p in plan_a.visitor_packets] == [
        p.packet_id for p in plan_b.visitor_packets
    ]


# --------------------------------------------------------------------------------------------
# 3. Golden determinism snapshot
# --------------------------------------------------------------------------------------------

_GOLDEN_HASH_PATH = FIXTURE_DIR / "golden-plan-hash.json"


def test_golden_determinism_snapshot() -> None:
    plan = _plan()
    golden = json.loads(_GOLDEN_HASH_PATH.read_text(encoding="utf-8"))
    assert plan.canonical_hash() == golden["plan_canonical_hash"], (
        "plan canonical_hash drifted from the committed golden snapshot -- if this change is "
        "intentional, regenerate tests/fixtures/bounded_review_packets/golden-plan-hash.json"
    )


# --------------------------------------------------------------------------------------------
# 4. Shuffled-input-order invariance
# --------------------------------------------------------------------------------------------


def test_shuffled_input_order_invariance() -> None:
    plan_original = _plan()

    shuffled_claims = _build_claim_accountability(
        CANDIDATE_TEXT, DEFAULT_FACTS, list(reversed(_default_claim_specs()))
    )
    shuffled_provenance = list(reversed(DEFAULT_PROVENANCE))
    shuffled_do_not_claim = list(reversed(DEFAULT_DO_NOT_CLAIM))

    plan_shuffled = _plan(
        claim_accountability=shuffled_claims,
        candidate_content_provenance=shuffled_provenance,
        do_not_claim=shuffled_do_not_claim,
    )

    assert brp.canonical_json(plan_original) == brp.canonical_json(plan_shuffled)


# --------------------------------------------------------------------------------------------
# 5. No fence/table split
# --------------------------------------------------------------------------------------------


def test_no_fence_or_table_unit_is_split_across_packets() -> None:
    plan = _plan()
    units = _atomic_units()
    for unit in units:
        if unit.kind not in {"fence", "table"}:
            continue
        factual_hits = sum(1 for p in plan.factual_packets if unit.unit_id in p.covered_unit_ids)
        visitor_hits = sum(1 for p in plan.visitor_packets if unit.unit_id in p.covered_unit_ids)
        assert factual_hits <= 1
        assert visitor_hits <= 1


# --------------------------------------------------------------------------------------------
# 6. No claim split
# --------------------------------------------------------------------------------------------


def test_no_claim_span_is_split_across_a_packet_boundary() -> None:
    plan = _plan()
    specs_by_id = {spec.claim_id: spec for spec in _default_claim_specs()}
    for packet in plan.factual_packets:
        for claim_id in packet.claim_ids:
            start, end = _claim_span(CANDIDATE_TEXT, specs_by_id[claim_id])
            assert packet.char_start <= start
            assert end <= packet.char_end


# --------------------------------------------------------------------------------------------
# 7. Factual-packet minimality
# --------------------------------------------------------------------------------------------


def test_factual_packet_minimality_excludes_facts_reachable_only_elsewhere() -> None:
    plan = _plan()
    claim_facts = {
        spec.claim_id: spec.fact_id for spec in _default_claim_specs() if spec.fact_id is not None
    }
    for packet in plan.factual_packets:
        reachable = {claim_facts[cid] for cid in packet.claim_ids if cid in claim_facts}
        for fact_id in packet.accepted_fact_ids:
            assert fact_id in reachable, (
                f"packet {packet.packet_id} carries fact {fact_id!r} not reachable from its own "
                "claim_ids"
            )
