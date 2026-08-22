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

import ast
import hashlib
import json
import pathlib
from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2
from readme_agent.readme.claim_accountability_models import (
    ReadmeClaimAccountabilityMapV1,
    ReadmeClaimAccountabilityV1,
)
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    PresentationSpanAdoptionV1,
    ReadmeDocumentPlanV1,
)
from readme_agent.specialists import bounded_review_packets as brp
from readme_agent.specialists.review_finding_grounding import GroundedReviewFindingV1

FIXTURE_DIR = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "bounded_review_packets"
CANDIDATE_PATH = FIXTURE_DIR / "candidate.md"

FACTUAL_PROMPT_SHA256 = hashlib.sha256(b"bounded-review-factual-prompt-v1").hexdigest()
VISITOR_PROMPT_SHA256 = hashlib.sha256(b"bounded-review-visitor-prompt-v1").hexdigest()

# Fits the ~26KB "Bundled Default Configuration" fence comfortably, so the default/"clean" fixture
# plan never surfaces an oversized_unit record by accident -- test_oversized_unit_* below uses a
# deliberately smaller budget to exercise that path on purpose.
DEFAULT_BUDGET_CHARS = 30_000


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_candidate() -> str:
    return CANDIDATE_PATH.read_text(encoding="utf-8")


CANDIDATE_TEXT = _read_candidate()


# --------------------------------------------------------------------------------------------
# Minimal-but-valid producer model builders
# --------------------------------------------------------------------------------------------

_FACT_VALUES: dict[str, object] = {
    "product.identity": "Widget Toolkit is a component library for building dashboards.",
    "product.audience": "Internal-tools teams building operational dashboards.",
    "product.problems_solved": "Assembling consistent dashboard widgets from scratch.",
    "product.capabilities": [
        "Drag-and-drop grid layout",
        "Theming",
        "Virtualized tables",
        "Accessible forms",
    ],
    "product.formats": ["JSON", "YAML"],
    "product.platforms": ["Web"],
    "installation.coordinates": "pip install widget-toolkit",
    "installation.verified_acquisition": {"registry": "pypi", "package": "widget-toolkit"},
    "example.minimal": {"language": "python", "code": "from widget_toolkit import Dashboard"},
    "documentation.links": ["https://example.invalid/docs"],
    "release.state": "2.3",
    "product.limitations": "No nested row grouping; pagination is experimental.",
    "product.compatibility": "Python 3.9+",
    "product.license": "MIT",
    "support.routes": "GitHub issue tracker",
    "relationship.commercial_foss": "A hosted managed edition is available separately.",
}


def _build_fact(field_name: str, value: object) -> FactRecordV2:
    return FactRecordV2(
        fact_id=f"{field_name}:primary",
        field=field_name,
        value=value,
        source=FactSourceV2(
            source_type="approved_documentation",
            location="fixture://source",
            source_revision="1",
        ),
        verification_state="verified",
        authoritative_owner="fixture-owner",
        confidence=1.0,
        affected_surfaces=["readme"],
    )


def _build_product_facts(overrides: dict[str, object] | None = None) -> ProductFactsV2:
    values = dict(_FACT_VALUES)
    if overrides:
        values.update(overrides)
    facts = [_build_fact(field, value) for field, value in values.items()]
    selected_fact_ids = {field: f"{field}:primary" for field in values}
    return ProductFactsV2(
        org_repo="acme/widget-toolkit",
        facts=facts,
        selected_fact_ids=selected_fact_ids,
    )


_PLACEHOLDER_HASH = _sha256("synthetic-source")


def _build_document_plan(candidate_text: str, facts: ProductFactsV2) -> ReadmeDocumentPlanV1:
    return ReadmeDocumentPlanV1(
        org_repo="acme/widget-toolkit",
        immutable_base_revision="0" * 40,
        facts_hash=facts.canonical_hash(),
        template_sha256=_PLACEHOLDER_HASH,
        source_sha256=_PLACEHOLDER_HASH,
        adoption=PresentationSpanAdoptionV1(
            already_adopted=True,
            source_document_sha256=_PLACEHOLDER_HASH,
            source_inner_sha256=_PLACEHOLDER_HASH,
            source_inner_bytes=0,
            preservation_check="byte_identical",
        ),
        operations=[],
        candidate_sha256=_sha256(candidate_text),
    )


@dataclass(frozen=True)
class _ClaimSpec:
    claim_id: str
    marker: str
    fact_id: str | None
    marker_end: str | None = None


def _claim_span(candidate_text: str, spec: _ClaimSpec) -> tuple[int, int]:
    start = candidate_text.index(spec.marker)
    if spec.marker_end is not None:
        end = candidate_text.index(spec.marker_end, start) + len(spec.marker_end)
    else:
        end = start + len(spec.marker)
    return start, end


def _build_claim_accountability(
    candidate_text: str,
    facts: ProductFactsV2,
    specs: list[_ClaimSpec],
) -> ReadmeClaimAccountabilityMapV1:
    claims = []
    for spec in specs:
        start, end = _claim_span(candidate_text, spec)
        byte_start = len(candidate_text[:start].encode("utf-8"))
        byte_end = len(candidate_text[:end].encode("utf-8"))
        content = candidate_text[start:end]
        claims.append(
            ReadmeClaimAccountabilityV1(
                claim_id=spec.claim_id,
                stage="candidate",
                origin="generated",
                source_byte_start=byte_start,
                source_byte_end=byte_end,
                content_sha256=_sha256(content),
                current_disposition="add",
                accepted_fact_ids=[spec.fact_id] if spec.fact_id else [],
                expected_disposition="accepted_fact" if spec.fact_id else "deferred_verification",
                survives_in_candidate=True,
                currently_accountable=True,
                rationale=f"synthetic fixture claim for {spec.claim_id}",
            )
        )
    return ReadmeClaimAccountabilityMapV1(
        org_repo="acme/widget-toolkit",
        facts_hash=facts.canonical_hash(),
        source_sha256=_PLACEHOLDER_HASH,
        candidate_sha256=_sha256(candidate_text),
        claims=claims,
    )


def _default_claim_specs() -> list[_ClaimSpec]:
    return [
        _ClaimSpec(
            "claim-overview-identity",
            "Widget Toolkit is a batteries-included component library for building "
            "desktop-style dashboards in the browser.",
            "product.identity:primary",
        ),
        _ClaimSpec(
            "claim-overview-problem",
            "It solves the recurring problem of assembling consistent, accessible dashboard "
            "widgets from scratch for every internal tool.",
            "product.problems_solved:primary",
        ),
        _ClaimSpec(
            "claim-capabilities",
            "- Drag-and-drop grid layout with responsive breakpoints.",
            "product.capabilities:primary",
            marker_end="- Accessible form controls audited against WCAG 2.1 AA.",
        ),
        _ClaimSpec(
            "claim-installation",
            "pip install widget-toolkit",
            "installation.coordinates:primary",
        ),
        _ClaimSpec(
            "claim-quickstart",
            'dashboard = Dashboard(theme="dark")\ndashboard.add_widget("clock")\n'
            "dashboard.render()",
            "example.minimal:primary",
        ),
        _ClaimSpec(
            "claim-api-release",
            "Every method below is verified against the public API surface for the 2.3 "
            "release line.",
            "release.state:primary",
        ),
        _ClaimSpec(
            "claim-limitations",
            "The virtualization layer does not yet support nested row grouping, and "
            "server-driven pagination is still experimental.",
            "product.limitations:primary",
        ),
        _ClaimSpec(
            "claim-support",
            "Bug reports and feature requests are tracked through the project issue "
            "tracker, and the maintainers respond within two business days.",
            "support.routes:primary",
        ),
        _ClaimSpec(
            "claim-license-terms",
            "Widget Toolkit is distributed under the MIT license, which permits commercial "
            "use, modification, and redistribution with attribution.",
            "product.license:primary",
        ),
        _ClaimSpec(
            "claim-license-relationship",
            "A hosted, fully managed edition with enterprise support is available "
            "separately; this repository contains only the open-source core.",
            "relationship.commercial_foss:primary",
        ),
    ]


def _default_provenance(candidate_text: str) -> list[CandidateContentProvenanceV1]:
    entries = []
    for provenance_id, marker, fact_id, rationale in (
        (
            "provenance-installation",
            "pip install widget-toolkit",
            "installation.coordinates:primary",
            "installation command matches the verified installation coordinates fact",
        ),
        (
            "provenance-license",
            "Widget Toolkit is distributed under the MIT license, which permits commercial "
            "use, modification, and redistribution with attribution.",
            "product.license:primary",
            "license prose matches the verified product license fact",
        ),
    ):
        start = candidate_text.index(marker)
        end = start + len(marker)
        byte_start = len(candidate_text[:start].encode("utf-8"))
        byte_end = len(candidate_text[:end].encode("utf-8"))
        entries.append(
            CandidateContentProvenanceV1(
                provenance_id=provenance_id,
                candidate_byte_start=byte_start,
                candidate_byte_end=byte_end,
                fact_ids=[fact_id],
                rationale=rationale,
            )
        )
    return entries


DEFAULT_DO_NOT_CLAIM = [
    {
        "fact_id": "unused.competitor_claim:primary",
        "field": "unused.competitor_claim",
        "reason": "unresolved_conflict",
    },
    {
        "fact_id": "unused.roadmap_claim:primary",
        "field": "unused.roadmap_claim",
        "reason": "conflicting_evidence",
    },
]

DEFAULT_FACTS = _build_product_facts()
DEFAULT_DOCUMENT_PLAN = _build_document_plan(CANDIDATE_TEXT, DEFAULT_FACTS)
DEFAULT_CLAIM_ACCOUNTABILITY = _build_claim_accountability(
    CANDIDATE_TEXT, DEFAULT_FACTS, _default_claim_specs()
)
DEFAULT_PROVENANCE = _default_provenance(CANDIDATE_TEXT)


def _plan(
    *,
    candidate_text: str = CANDIDATE_TEXT,
    document_plan: ReadmeDocumentPlanV1 = DEFAULT_DOCUMENT_PLAN,
    claim_accountability: ReadmeClaimAccountabilityMapV1 = DEFAULT_CLAIM_ACCOUNTABILITY,
    product_facts: ProductFactsV2 = DEFAULT_FACTS,
    do_not_claim: list[dict] | None = None,
    candidate_content_provenance: list[CandidateContentProvenanceV1] | None = None,
    budget_chars: int = DEFAULT_BUDGET_CHARS,
    **kwargs: object,
) -> brp.BoundedReviewPlanV1:
    return brp.plan_bounded_review_packets(
        candidate_text=candidate_text,
        document_plan=document_plan,
        claim_accountability=claim_accountability,
        product_facts=product_facts,
        do_not_claim=DEFAULT_DO_NOT_CLAIM if do_not_claim is None else do_not_claim,
        candidate_content_provenance=(
            DEFAULT_PROVENANCE
            if candidate_content_provenance is None
            else candidate_content_provenance
        ),
        budget_chars=budget_chars,
        factual_prompt_sha256=FACTUAL_PROMPT_SHA256,
        visitor_prompt_sha256=VISITOR_PROMPT_SHA256,
        **kwargs,
    )


def _atomic_units(
    *,
    candidate_text: str = CANDIDATE_TEXT,
    claim_accountability: ReadmeClaimAccountabilityMapV1 = DEFAULT_CLAIM_ACCOUNTABILITY,
    product_facts: ProductFactsV2 = DEFAULT_FACTS,
    candidate_content_provenance: list[CandidateContentProvenanceV1] | None = None,
) -> tuple[brp.AtomicUnitV1, ...]:
    provenance = (
        DEFAULT_PROVENANCE if candidate_content_provenance is None else candidate_content_provenance
    )
    return brp.build_atomic_units(candidate_text, claim_accountability, product_facts, provenance)


def _accept_finding(packet: brp.BoundedPacketV1) -> GroundedReviewFindingV1:
    if isinstance(packet, brp.BoundedVisitorPacketV1):
        quote = packet.section_text[: min(40, len(packet.section_text))]
        return GroundedReviewFindingV1(
            finding_id="finding.accept.visitor",
            kind="quality",
            criterion="clarity",
            section=packet.section_path,
            claim="Section reads clearly for a visitor.",
            quoted_candidate_span=quote,
            disposition="supports_acceptance",
            polarity_result="not_applicable",
        )
    assert packet.accepted_fact_ids, f"factual packet {packet.packet_id} has no accepted facts"
    fact_id = packet.accepted_fact_ids[0]
    quote = packet.unit_text[: min(40, len(packet.unit_text))]
    return GroundedReviewFindingV1(
        finding_id="finding.accept.factual",
        kind="factual",
        criterion="claim_grounding",
        section=packet.section_path,
        claim="Claim is grounded in the cited fact.",
        quoted_candidate_span=quote,
        disposition="supports_acceptance",
        fact_id=fact_id,
        evidence_excerpt="synthetic accepted evidence excerpt",
        evidence_location="fixture://source",
        expected_polarity="positive_implementation",
        observed_polarity="positive_implementation",
        polarity_result="supports",
    )


def _accept_result_for(packet: brp.BoundedPacketV1) -> brp.BoundedPacketResultV1:
    return brp.BoundedPacketResultV1(
        packet_id=packet.packet_id,
        facet=packet.facet,
        candidate_sha256=packet.candidate_sha256,
        packet_sha256=packet.packet_sha256,
        prompt_contract_hash=packet.prompt_contract_hash,
        input_contract_hash=packet.input_contract_hash,
        verdict="ACCEPT",
        reasoning="Synthetic accept for test fixture.",
        findings=(_accept_finding(packet),),
    )


def _reject_finding(packet: brp.BoundedPacketV1) -> GroundedReviewFindingV1:
    if isinstance(packet, brp.BoundedVisitorPacketV1):
        quote = packet.section_text[: min(40, len(packet.section_text))]
        return GroundedReviewFindingV1(
            finding_id="finding.reject.visitor",
            kind="quality",
            criterion="clarity",
            section=packet.section_path,
            claim="Section prose needs a rewrite for clarity.",
            quoted_candidate_span=quote,
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Rewrite the opening sentence for clarity.",
        )
    fact_id = packet.accepted_fact_ids[0]
    quote = packet.unit_text[: min(40, len(packet.unit_text))]
    return GroundedReviewFindingV1(
        finding_id="finding.reject.factual",
        kind="factual",
        criterion="claim_grounding",
        section=packet.section_path,
        claim="Claim needs stronger grounding.",
        quoted_candidate_span=quote,
        disposition="requires_repair",
        fact_id=fact_id,
        evidence_excerpt="synthetic weak evidence excerpt",
        evidence_location="fixture://source",
        expected_polarity="positive_implementation",
        observed_polarity="positive_implementation",
        polarity_result="supports",
        required_repair="Cite the fact more precisely.",
    )


def _reject_result_for(packet: brp.BoundedPacketV1) -> brp.BoundedPacketResultV1:
    criterion = "clarity" if isinstance(packet, brp.BoundedVisitorPacketV1) else "claim_grounding"
    return brp.BoundedPacketResultV1(
        packet_id=packet.packet_id,
        facet=packet.facet,
        candidate_sha256=packet.candidate_sha256,
        packet_sha256=packet.packet_sha256,
        prompt_contract_hash=packet.prompt_contract_hash,
        input_contract_hash=packet.input_contract_hash,
        verdict="REJECT_REPAIRABLE",
        reasoning="Synthetic rejection for test fixture.",
        failed_criteria=(criterion,),
        required_repair="See finding-level repair instruction.",
        findings=(_reject_finding(packet),),
    )


def _all_required_packets(plan: brp.BoundedReviewPlanV1) -> tuple[brp.BoundedPacketV1, ...]:
    return (*plan.factual_packets, *plan.visitor_packets)


def _all_accept_results(
    plan: brp.BoundedReviewPlanV1,
    *,
    overrides: dict[str, brp.BoundedPacketResultV1] | None = None,
) -> dict[str, brp.BoundedPacketResultV1]:
    results = {
        packet.packet_id: _accept_result_for(packet) for packet in _all_required_packets(plan)
    }
    if overrides:
        results.update(overrides)
    return results


# --------------------------------------------------------------------------------------------
# 1. Synthetic candidate plans successfully; every packet within budget
# --------------------------------------------------------------------------------------------


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


# --------------------------------------------------------------------------------------------
# 8. Full visitor + factual coverage
# --------------------------------------------------------------------------------------------


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


# --------------------------------------------------------------------------------------------
# 13. Missing packet result -> INCOMPLETE
# --------------------------------------------------------------------------------------------


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
# 15. Conflicting overlapping packets -> CONFLICT
# --------------------------------------------------------------------------------------------


def test_conflicting_overlapping_packets_yield_conflict() -> None:
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
    assert aggregate.overall == "CONFLICT"
    assert set(overlap.packet_ids) <= set(aggregate.conflicting_packet_ids)


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


# --------------------------------------------------------------------------------------------
# 22. No provider/LLM client import anywhere in the module
# --------------------------------------------------------------------------------------------


def test_module_never_calls_a_provider() -> None:
    source_path = pathlib.Path(brp.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    forbidden_markers = ("llm", "reviewer_client", "ForcedToolClient", "capabilities.dispatcher")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        for name in names:
            lowered = name.casefold()
            assert not any(marker.casefold() in lowered for marker in forbidden_markers), (
                f"forbidden provider-adjacent import found: {name!r}"
            )
    source_text = source_path.read_text(encoding="utf-8")
    for marker in ("reviewer_client", "LiveForcedToolClient", "dispatch_tool_call"):
        assert marker not in source_text


# --------------------------------------------------------------------------------------------
# 23. Hash-mismatch raise (dedicated, literal required-tests item)
# --------------------------------------------------------------------------------------------


def test_plan_raises_on_mismatched_candidate_facts_plan_triple() -> None:
    other_facts = _build_product_facts(overrides={"release.state": "9.9"})
    mismatched_claims = DEFAULT_CLAIM_ACCOUNTABILITY.model_copy(
        update={"facts_hash": other_facts.canonical_hash()}
    )
    with pytest.raises(brp.BoundedReviewInputMismatchError):
        _plan(claim_accountability=mismatched_claims)


# --------------------------------------------------------------------------------------------
# 24. Unpacketizable oversized unit -> explicit blocking record
# --------------------------------------------------------------------------------------------


def test_oversized_unit_produces_explicit_blocking_record() -> None:
    plan = _plan(budget_chars=10_000)
    oversized = [r for r in plan.unpacketizable if r.reason == "oversized_unit"]
    assert oversized
    assert any(record.section_path == "bundled-default-configuration" for record in oversized)
    for record in oversized:
        assert record.unit_kind is not None
        assert record.required_min_budget is not None
        assert record.required_min_budget > 10_000


# --------------------------------------------------------------------------------------------
# 25. Internally inconsistent envelope rejected by its own validator
# --------------------------------------------------------------------------------------------


def test_inconsistent_envelope_rejected_by_own_validator() -> None:
    plan = _plan()
    packet = plan.factual_packets[0]
    fact_id = packet.accepted_fact_ids[0]
    blocking_finding = GroundedReviewFindingV1(
        finding_id="finding.blocks.only",
        kind="factual",
        criterion="claim_grounding",
        section=packet.section_path,
        claim="This fact is contradicted by other evidence.",
        quoted_candidate_span=packet.unit_text[: min(40, len(packet.unit_text))],
        disposition="blocks",
        fact_id=fact_id,
        evidence_excerpt="synthetic contradicting evidence excerpt",
        evidence_location="fixture://source",
        expected_polarity="positive_implementation",
        observed_polarity="explicit_constraint",
        polarity_result="contradicts",
    )
    with pytest.raises(ValidationError):
        brp.BoundedPacketResultV1(
            packet_id=packet.packet_id,
            facet=packet.facet,
            candidate_sha256=packet.candidate_sha256,
            packet_sha256=packet.packet_sha256,
            prompt_contract_hash=packet.prompt_contract_hash,
            input_contract_hash=packet.input_contract_hash,
            verdict="ACCEPT",
            reasoning="Inconsistent: ACCEPT cannot carry only a blocking finding.",
            findings=(blocking_finding,),
        )
