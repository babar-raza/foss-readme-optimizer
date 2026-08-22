"""Module-level pilot for bounded_review_packets.py against the REAL committed proof candidate.

Read-only: loads real committed evidence, calls the module's pure functions, prints a report.
Writes nothing to the repo, makes zero network/provider calls. Run from anywhere with this
repo's own virtualenv active (needs pydantic + this repo's src/ on sys.path):

    python module_handoffs/bounded-review/e731ea56ebb5/pilot/real_candidate_pilot.py

Produced the findings in ../PILOT_VERIFICATION_AND_KNOWN_BUG.md -- re-run this script to
reproduce every number cited there, including the confirmed zero-factual-coverage bug and the
diagnostic that shows the fix is narrowly scoped.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent.facts.schema_v2 import (  # noqa: E402
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
)
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1  # noqa: E402
from readme_agent.specialists import bounded_review_packets as brp  # noqa: E402

EVID = REPO_ROOT / "plans" / "investigations" / "evidence" / "qwen-section-engine-integration"
PROMPT_HASH_A = "f0" * 32
PROMPT_HASH_B = "c1" * 32


def hdr(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main() -> None:
    hdr("STEP 0 -- load the REAL committed proof candidate + real document plan")
    candidate_text = (EVID / "candidate.md").read_text(encoding="utf-8")
    candidate_bytes = candidate_text.encode("utf-8")
    candidate_sha256 = hashlib.sha256(candidate_bytes).hexdigest()
    print("candidate.md real byte length:", len(candidate_bytes))
    print("candidate.md real sha256:", candidate_sha256)

    plan_raw = json.loads((EVID / "readme-document-plan.json").read_text(encoding="utf-8"))
    real_document_plan = ReadmeDocumentPlanV1.model_validate(plan_raw)
    real_claim_accountability = real_document_plan.claim_accountability
    assert real_claim_accountability is not None
    print("document_plan.org_repo:", real_document_plan.org_repo)
    print(
        "document_plan.candidate_sha256 == recomputed:",
        real_document_plan.candidate_sha256 == candidate_sha256,
    )
    print(
        "claim_accountability.candidate_sha256 == recomputed:",
        real_claim_accountability.candidate_sha256 == candidate_sha256,
    )
    print("real claim count:", len(real_claim_accountability.claims))
    print("real document_plan.facts_hash:", real_document_plan.facts_hash)

    hdr("STEP 1 -- FAIL-CLOSED PROOF: real candidate + real plan + best-available real facts file")
    closest_facts_path = (
        REPO_ROOT
        / "data"
        / "check_classification_fixtures"
        / "aspose-3d-foss__Aspose.3D-FOSS-for-Python"
        / "facts"
        / "product-facts.json"
    )
    closest_facts = ProductFactsV2.model_validate(
        json.loads(closest_facts_path.read_text(encoding="utf-8"))
    )
    print(
        "closest available real facts file:",
        closest_facts_path.name,
        "(from a different evidence campaign for the same repo)",
    )
    print("its canonical_hash():", closest_facts.canonical_hash())
    print("does NOT equal document_plan.facts_hash -- the original facts.json behind this exact")
    print("candidate was not preserved in committed evidence. This is real, unmodified data on")
    print("both sides -- the mismatch itself is the real-world condition under test.")
    try:
        brp.plan_bounded_review_packets(
            candidate_text=candidate_text,
            document_plan=real_document_plan,
            claim_accountability=real_claim_accountability,
            product_facts=closest_facts,
            budget_chars=30_000,
            factual_prompt_sha256=PROMPT_HASH_A,
            visitor_prompt_sha256=PROMPT_HASH_B,
        )
        print("RESULT: NO EXCEPTION RAISED -- THIS WOULD BE A BUG (fail-closed contract broken)")
    except brp.BoundedReviewInputMismatchError as exc:
        print("RESULT: BoundedReviewInputMismatchError raised, as required. Message:")
        print(" ", exc)

    hdr("STEP 2 -- build a real-claim-derived, self-consistent facts corpus")
    fact_ids: set[str] = set()
    for claim in real_claim_accountability.claims:
        fact_ids.update(claim.accepted_fact_ids)
    fact_ids_sorted = sorted(fact_ids)
    print("distinct real fact_ids referenced across all real claims:", len(fact_ids_sorted))
    print("first 5:", fact_ids_sorted[:5])

    records = [
        FactRecordV2(
            fact_id=fid,
            field=fid,
            value=f"<pilot-derived-placeholder:{fid}>",
            source=FactSourceV2(
                source_type="agent_drafted",
                location="bounded_review_pilot#derived-from-claim-accountability",
                source_revision=real_document_plan.immutable_base_revision,
            ),
            verification_state="verified",
            authoritative_owner="bounded_review_pilot",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for fid in fact_ids_sorted
    ]
    # ProductFactsV2 requires a selection for all 16 canonical required fields; the real
    # claim-referenced fact_ids don't happen to use those exact dotted names, so fill the gap
    # with explicitly-labeled stub records -- these are NOT presented as real product facts.
    stub_records = [
        FactRecordV2(
            fact_id=f"pilot.stub:{field}",
            field=field,
            value=f"<pilot-stub-not-a-real-fact:{field}>",
            source=FactSourceV2(
                source_type="agent_drafted",
                location="bounded_review_pilot#required-field-stub",
                source_revision=real_document_plan.immutable_base_revision,
            ),
            verification_state="verified",
            authoritative_owner="bounded_review_pilot",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    all_records = records + stub_records
    selections = {field: f"pilot.stub:{field}" for field in REQUIRED_PRODUCT_FIELDS}
    print(
        "added",
        len(stub_records),
        "explicitly-labeled stub facts to satisfy ProductFactsV2's required-field-selection",
        "completeness rule (unrelated to the real claim-referenced fact_ids, which remain used",
        "for claim->fact linkage below)",
    )
    derived_facts = ProductFactsV2(
        org_repo=real_document_plan.org_repo,
        facts=all_records,
        selected_fact_ids=selections,
    )
    derived_facts_hash = derived_facts.canonical_hash()
    print("derived facts corpus canonical_hash():", derived_facts_hash)
    print("NOTE: values are explicit placeholders, not fabricated real product claims -- only the")
    print("fact_id/field identifiers are real (pulled from the real claim_accountability).")

    rebound_document_plan = real_document_plan.model_copy(update={"facts_hash": derived_facts_hash})
    rebound_claim_accountability = real_claim_accountability.model_copy(
        update={"facts_hash": derived_facts_hash}
    )
    print("rebound copies: candidate text, claim spans, claim IDs, dispositions all UNCHANGED --")
    print("only the facts_hash field on the two copies was re-stamped to match derived_facts.")

    hdr("STEP 3 -- HAPPY PATH: plan the REAL candidate, budget_chars=30000")
    plan1 = brp.plan_bounded_review_packets(
        candidate_text=candidate_text,
        document_plan=rebound_document_plan,
        claim_accountability=rebound_claim_accountability,
        product_facts=derived_facts,
        budget_chars=30_000,
        factual_prompt_sha256=PROMPT_HASH_A,
        visitor_prompt_sha256=PROMPT_HASH_B,
    )
    print("factual packets:", len(plan1.factual_packets))
    print("visitor packets:", len(plan1.visitor_packets))
    print("unpacketizable records:", len(plan1.unpacketizable))
    fsizes = [len(brp._packet_text(p)) for p in plan1.factual_packets]
    vsizes = [len(brp._packet_text(p)) for p in plan1.visitor_packets]
    print(
        "factual packet text sizes: min=%d max=%d" % (min(fsizes, default=0), max(fsizes, default=0))
    )
    print("visitor packet text sizes: min=%d max=%d" % (min(vsizes, default=0), max(vsizes, default=0)))
    all_packets = list(plan1.factual_packets) + list(plan1.visitor_packets)
    print(
        "all packets <= budget_chars (30000):",
        all(len(brp._packet_text(p)) <= 30_000 for p in all_packets),
    )

    hdr("STEP 3B -- DIAGNOSTIC: real candidate-stage claim filter never matches real data")
    stage_counts = Counter(c.stage for c in rebound_claim_accountability.claims)
    survives_by_stage = {
        stage: Counter(
            c.survives_in_candidate for c in rebound_claim_accountability.claims if c.stage == stage
        )
        for stage in ("candidate", "source")
    }
    print("claim stage counts:", dict(stage_counts))
    print("survives_in_candidate by stage:", survives_by_stage)
    matching_filter = [
        c
        for c in rebound_claim_accountability.claims
        if c.stage == "candidate" and c.survives_in_candidate
    ]
    print(
        "claims matching the module's real filter (stage==candidate and survives_in_candidate):",
        len(matching_filter),
    )
    print("-> this is WHY factual packets came out as 0 above.")

    accountable_candidate_claims = [
        c
        for c in rebound_claim_accountability.claims
        if c.stage == "candidate" and c.currently_accountable and c.accepted_fact_ids
    ]
    print(
        "candidate-stage claims with currently_accountable=True and >=1 accepted_fact_ids:",
        len(accountable_candidate_claims),
    )
    print("(the real, populated signal -- confirmed against claim_accountability.py's")
    print(" survives_in_candidate=None literal for every stage='candidate' claim)")

    print()
    print("Diagnostic-only simulation (NOT a module edit): copy the real claim records with")
    print("survives_in_candidate overridden to match currently_accountable, to check whether the")
    print("packet-building logic downstream of the filter is otherwise sound once given data in")
    print("the shape the filter expects.")
    simulated_claims = [
        c.model_copy(update={"survives_in_candidate": c.currently_accountable})
        if c.stage == "candidate"
        else c
        for c in rebound_claim_accountability.claims
    ]
    simulated_ca = rebound_claim_accountability.model_copy(update={"claims": simulated_claims})
    plan_simulated = brp.plan_bounded_review_packets(
        candidate_text=candidate_text,
        document_plan=rebound_document_plan,
        claim_accountability=simulated_ca,
        product_facts=derived_facts,
        budget_chars=30_000,
        factual_prompt_sha256=PROMPT_HASH_A,
        visitor_prompt_sha256=PROMPT_HASH_B,
    )
    print("with the filter's precondition satisfied -- factual packets:", len(plan_simulated.factual_packets))
    print("visitor packets:", len(plan_simulated.visitor_packets))
    print("unpacketizable:", len(plan_simulated.unpacketizable))
    if plan_simulated.factual_packets:
        fsizes2 = [len(brp._packet_text(p)) for p in plan_simulated.factual_packets]
        print(
            "factual packet sizes: min=%d max=%d, all<=budget: %s"
            % (min(fsizes2), max(fsizes2), all(s <= 30_000 for s in fsizes2))
        )
        claim_ids_covered = {cid for p in plan_simulated.factual_packets for cid in p.claim_ids}
        print("distinct claim_ids covered across factual packets:", len(claim_ids_covered))

    hdr("STEP 4 -- DETERMINISM: rerun identical inputs, diff canonical output")
    plan2 = brp.plan_bounded_review_packets(
        candidate_text=candidate_text,
        document_plan=rebound_document_plan,
        claim_accountability=rebound_claim_accountability,
        product_facts=derived_facts,
        budget_chars=30_000,
        factual_prompt_sha256=PROMPT_HASH_A,
        visitor_prompt_sha256=PROMPT_HASH_B,
    )
    print("plan1.canonical_hash():", plan1.canonical_hash())
    print("plan2.canonical_hash():", plan2.canonical_hash())
    print("byte-identical rerun:", plan1.canonical_hash() == plan2.canonical_hash())

    hdr("STEP 5 -- COVERAGE LEDGER on the real candidate")
    atomic_units = brp.build_atomic_units(candidate_text, rebound_claim_accountability, derived_facts)
    ledger = brp.build_coverage_ledger(plan1, atomic_units=atomic_units)
    validation = brp.validate_coverage_ledger(ledger)
    print("atomic units:", len(atomic_units))
    print("visitor_spans covered:", len(ledger.visitor_spans))
    print("factual_spans covered:", len(ledger.factual_spans))
    print("excluded_spans (e.g. API-inventory):", len(ledger.excluded_spans))
    excluded_by_section = sorted({ex.section_path for ex in ledger.excluded_spans})
    for section_path in excluded_by_section:
        print("  excluded section:", section_path)
    print("overlaps:", len(ledger.overlaps))
    print("coverage is_complete:", validation.is_complete)
    print("coverage has_blocking_gaps:", validation.has_blocking_gaps)

    hdr("STEP 6 -- SELECTIVE INVALIDATION on the real candidate (same-length in-place edit)")
    claimed_spans = sorted(
        {(c.source_byte_start, c.source_byte_end) for c in rebound_claim_accountability.claims}
    )
    edit_start = None
    for a_end, b_start in zip([s[1] for s in claimed_spans], [s[0] for s in claimed_spans[1:]]):
        if b_start - a_end >= 80:
            edit_start = a_end + 10
            break
    if edit_start is None:
        print("no safe unclaimed gap >=80 bytes found; skipping this step honestly (not faked)")
    else:
        edit_len = 40
        replacement = b"X" * edit_len
        edited_bytes = (
            candidate_bytes[:edit_start] + replacement + candidate_bytes[edit_start + edit_len :]
        )
        edited_text = edited_bytes.decode("utf-8", errors="strict")
        edited_sha256 = hashlib.sha256(edited_bytes).hexdigest()
        print(
            "edited a claim-free 40-byte span at offset",
            edit_start,
            "-- length unchanged, so all real claim byte spans stay structurally valid",
        )
        edited_document_plan = rebound_document_plan.model_copy(update={"candidate_sha256": edited_sha256})
        edited_claim_accountability = rebound_claim_accountability.model_copy(
            update={"candidate_sha256": edited_sha256}
        )
        plan_edited = brp.plan_bounded_review_packets(
            candidate_text=edited_text,
            document_plan=edited_document_plan,
            claim_accountability=edited_claim_accountability,
            product_facts=derived_facts,
            budget_chars=30_000,
            factual_prompt_sha256=PROMPT_HASH_A,
            visitor_prompt_sha256=PROMPT_HASH_B,
        )
        invalidated = brp.invalidated_packet_ids(plan1, plan_edited)
        total_slots = len(plan1.factual_packets) + len(plan1.visitor_packets)
        print("total packet-identities before edit:", total_slots)
        print("invalidated by editing ONE 40-byte claim-free span:", len(invalidated))
        print("invalidated packet_ids:", sorted(invalidated))

    hdr("STEP 7 -- FACT-VALUE CHANGE (against the UNFIXED plan1 -- vacuous, see STEP 7B)")
    changed_records = list(records)
    if changed_records:
        target = changed_records[0]
        changed_records[0] = target.model_copy(update={"value": "<pilot-derived-CHANGED-value>"})
        changed_facts = ProductFactsV2(
            org_repo=derived_facts.org_repo,
            facts=changed_records + stub_records,
            selected_fact_ids=derived_facts.selected_fact_ids,
        )
        changed_hash = changed_facts.canonical_hash()
        plan_fact_changed = brp.plan_bounded_review_packets(
            candidate_text=candidate_text,
            document_plan=rebound_document_plan.model_copy(update={"facts_hash": changed_hash}),
            claim_accountability=rebound_claim_accountability.model_copy(update={"facts_hash": changed_hash}),
            product_facts=changed_facts,
            budget_chars=30_000,
            factual_prompt_sha256=PROMPT_HASH_A,
            visitor_prompt_sha256=PROMPT_HASH_B,
        )
        invalidated_by_fact = brp.invalidated_packet_ids(plan1, plan_fact_changed)
        visitor_ids_before = {p.packet_id for p in plan1.visitor_packets}
        visitor_ids_after = {p.packet_id for p in plan_fact_changed.visitor_packets}
        print("changed value of fact_id:", target.fact_id)
        print("factual packets invalidated:", len(invalidated_by_fact), "(vacuous -- plan1 has 0)")
        print("visitor packet set unchanged (before == after):", visitor_ids_before == visitor_ids_after)

    hdr("STEP 7B -- FACT-VALUE CHANGE re-run against the CORRECTED simulation (non-vacuous)")
    sim_records = list(records)
    if sim_records:
        sim_target = sim_records[0]
        sim_records[0] = sim_target.model_copy(update={"value": "<pilot-derived-CHANGED-value>"})
        sim_changed_facts = ProductFactsV2(
            org_repo=derived_facts.org_repo,
            facts=sim_records + stub_records,
            selected_fact_ids=derived_facts.selected_fact_ids,
        )
        sim_changed_hash = sim_changed_facts.canonical_hash()
        plan_sim_fact_changed = brp.plan_bounded_review_packets(
            candidate_text=candidate_text,
            document_plan=rebound_document_plan.model_copy(update={"facts_hash": sim_changed_hash}),
            claim_accountability=simulated_ca.model_copy(update={"facts_hash": sim_changed_hash}),
            product_facts=sim_changed_facts,
            budget_chars=30_000,
            factual_prompt_sha256=PROMPT_HASH_A,
            visitor_prompt_sha256=PROMPT_HASH_B,
        )
        sim_invalidated = brp.invalidated_packet_ids(plan_simulated, plan_sim_fact_changed)
        sim_visitor_before = {p.packet_id for p in plan_simulated.visitor_packets}
        sim_visitor_after = {p.packet_id for p in plan_sim_fact_changed.visitor_packets}
        print("changed value of fact_id:", sim_target.fact_id)
        print("total factual packets in plan_simulated:", len(plan_simulated.factual_packets))
        print("factual packets invalidated by this one fact change:", len(sim_invalidated))
        print("visitor packet set unchanged (before == after):", sim_visitor_before == sim_visitor_after)

    hdr("DONE")


if __name__ == "__main__":
    main()
