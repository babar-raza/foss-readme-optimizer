"""Bounded review reuses only exact validated packet results."""

from __future__ import annotations

import json

import pytest
from bounded_review_result_support import _accept_finding
from bounded_review_test_support import (
    CANDIDATE_TEXT,
    DEFAULT_FACTS,
    _atomic_units,
    _build_claim_accountability,
    _build_document_plan,
    _default_claim_specs,
    _FailIfCalledClient,
    _PacketSequenceClient,
    _plan,
)

from readme_agent.evidence.writer import refresh_sha256sums, verify_sha256sums
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.presentation.visitor_contract import build_presentation_visitor_contract
from readme_agent.specialists import bounded_review_packets as brp
from readme_agent.specialists.bounded_review_cache import (
    BoundedReviewCacheContextV1,
    cache_key_for_packet,
    legacy_cache_key_for_packet,
    legacy_packet_identity_cache_key_for_packet,
    load_bounded_review_packet_cache,
    write_bounded_review_packet_cache,
)
from readme_agent.specialists.bounded_review_execution import execute_bounded_review
from readme_agent.specialists.bounded_review_execution_cache import BoundedReviewPacketCache
from readme_agent.specialists.bounded_review_hashing import _canonical_hash
from readme_agent.specialists.bounded_review_visitor_scope import (
    bounded_visitor_contract,
    bounded_visitor_scope,
    bounded_visitor_scope_errors,
)
from readme_agent.specialists.review_candidate_anchors import build_candidate_review_anchors
from readme_agent.supervisor.local_poc_bounded_review_recovery import (
    recover_interrupted_bounded_review_cache_write,
    recover_migrated_bounded_review_cache_entries,
)


def _headings() -> list[str]:
    return [
        line.removeprefix("## ").strip()
        for line in CANDIDATE_TEXT.splitlines()
        if line.startswith("## ")
    ]


def _cache_context() -> BoundedReviewCacheContextV1:
    return BoundedReviewCacheContextV1(
        source_revision="a" * 40,
        blind_model="qwen3-next",
        factual_model="qwen3-next",
        blind_schema_sha256="b" * 64,
        factual_schema_sha256="c" * 64,
        facts_hash="d" * 64,
        provenance_hash="e" * 64,
        blind_sampling_parameters={"temperature": 0.0, "max_tokens": 3000},
        factual_sampling_parameters={"temperature": 0.0, "max_tokens": 6000},
    )


def test_exact_packet_results_are_reused_without_provider_calls(tmp_path) -> None:
    plan = _plan()
    ledger = brp.build_coverage_ledger(plan, atomic_units=_atomic_units())
    visitor_packets = list(plan.visitor_packets)
    factual_packets = list(plan.factual_packets)
    arguments = {
        "org_repo": "acme/widget-toolkit",
        "candidate_text": CANDIDATE_TEXT,
        "product_facts": DEFAULT_FACTS.model_dump(mode="json"),
        "visitor_contract": build_presentation_visitor_contract(
            applicable_h2_headings=_headings(),
            primary_example_language="python",
        ),
        "plan": plan,
        "coverage_ledger": ledger,
        "blind_prompt_id": "blind_readme_quality_review",
        "factual_prompt_id": "factual_readme_plan_review",
        "cache_dir": tmp_path / "packet-cache",
        "cache_context": _cache_context(),
    }

    first = execute_bounded_review(
        **arguments,
        blind_client=_PacketSequenceClient(visitor_packets),
        factual_client=_PacketSequenceClient(factual_packets),
    )
    second = execute_bounded_review(
        **arguments,
        blind_client=_FailIfCalledClient(),
        factual_client=_FailIfCalledClient(),
    )

    assert first.packet_results == second.packet_results
    assert second.aggregate.overall == "ACCEPT"
    cache_events = [
        item
        for item in second.grounding_history
        if item.get("context_mode") == "bounded_packet_cache_reuse"
    ]
    assert len(cache_events) == len(visitor_packets) + len(factual_packets)


def test_interrupted_packet_cache_writes_are_validated_and_resealed(tmp_path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "manifest.json").write_text('{"sealed":true}\n', encoding="utf-8")
    nested_inventory = bundle / "superseded" / "prior" / "sha256sums.txt"
    nested_inventory.parent.mkdir(parents=True)
    nested_inventory.write_text("nested inventory is independently sealed\n", encoding="utf-8")
    refresh_sha256sums(bundle)
    plan = _plan()
    context = _cache_context()
    cache_dir = bundle / "review" / "bounded-packet-cache"

    execute_bounded_review(
        org_repo="acme/widget-toolkit",
        candidate_text=CANDIDATE_TEXT,
        product_facts=DEFAULT_FACTS.model_dump(mode="json"),
        visitor_contract=build_presentation_visitor_contract(
            applicable_h2_headings=_headings(),
            primary_example_language="python",
        ),
        plan=plan,
        coverage_ledger=brp.build_coverage_ledger(plan, atomic_units=_atomic_units()),
        blind_client=_PacketSequenceClient(list(plan.visitor_packets)),
        factual_client=_PacketSequenceClient(list(plan.factual_packets)),
        blind_prompt_id="blind_readme_quality_review",
        factual_prompt_id="factual_readme_plan_review",
        cache_dir=cache_dir,
        cache_context=context,
    )

    assert not verify_sha256sums(bundle)
    assert recover_interrupted_bounded_review_cache_write(
        bundle,
        org_repo="acme/widget-toolkit",
        source_revision=context.source_revision,
    )
    assert verify_sha256sums(bundle)


def test_interrupted_packet_cache_recovery_rejects_unrelated_extra(tmp_path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "manifest.json").write_text('{"sealed":true}\n', encoding="utf-8")
    refresh_sha256sums(bundle)
    unrelated = bundle / "candidate" / "README.md"
    unrelated.parent.mkdir()
    unrelated.write_text("# Unexpected\n", encoding="utf-8")
    inventory_before = (bundle / "sha256sums.txt").read_bytes()

    assert not recover_interrupted_bounded_review_cache_write(
        bundle,
        org_repo="acme/widget-toolkit",
        source_revision="a" * 40,
    )
    assert (bundle / "sha256sums.txt").read_bytes() == inventory_before


def _seal_bundle_with_one_packet_cache_entry(bundle):
    """Build a real, sealed bundle with at least one bounded-review packet cache file."""

    bundle.mkdir()
    (bundle / "manifest.json").write_text('{"sealed":true}\n', encoding="utf-8")
    plan = _plan()
    context = _cache_context()
    cache_dir = bundle / "review" / "bounded-packet-cache"
    execute_bounded_review(
        org_repo="acme/widget-toolkit",
        candidate_text=CANDIDATE_TEXT,
        product_facts=DEFAULT_FACTS.model_dump(mode="json"),
        visitor_contract=build_presentation_visitor_contract(
            applicable_h2_headings=_headings(),
            primary_example_language="python",
        ),
        plan=plan,
        coverage_ledger=brp.build_coverage_ledger(plan, atomic_units=_atomic_units()),
        blind_client=_PacketSequenceClient(list(plan.visitor_packets)),
        factual_client=_PacketSequenceClient(list(plan.factual_packets)),
        blind_prompt_id="blind_readme_quality_review",
        factual_prompt_id="factual_readme_plan_review",
        cache_dir=cache_dir,
        cache_context=context,
    )
    refresh_sha256sums(bundle)
    assert verify_sha256sums(bundle)
    cache_files = sorted(cache_dir.glob("*.json"))
    assert cache_files
    return cache_files[0], context


def test_migrated_packet_cache_entry_is_validated_and_resealed(tmp_path) -> None:
    """`BoundedReviewPacketCache.load()` can rewrite a cache entry's bytes in place at its
    existing identity-keyed filename when it migrates a legacy cache key forward -- found live
    against `aspose-font-foss`'s sealed snapshot (41 files rewritten this way, zero added). The
    existing `recover_interrupted_bounded_review_cache_write` only tolerates *added* files and
    must correctly refuse this case; the new sibling must repair it."""

    bundle = tmp_path / "bundle"
    entry_path, context = _seal_bundle_with_one_packet_cache_entry(bundle)
    inventory_before = (bundle / "sha256sums.txt").read_bytes()

    cached = json.loads(entry_path.read_text(encoding="utf-8"))
    cached["grounding_history"] = [
        *cached["grounding_history"],
        {
            "role": "blind_quality",
            "attempt": 0,
            "context_mode": "bounded_packet_cache_identity_migration",
            "valid": True,
            "errors": [],
            "packet_id": cached["packet_id"],
            "legacy_cache_key": "0" * 64,
            "cache_key": cached["cache_key"],
        },
    ]
    entry_path.write_text(json.dumps(cached), encoding="utf-8")

    assert not verify_sha256sums(bundle)
    assert not recover_interrupted_bounded_review_cache_write(
        bundle,
        org_repo="acme/widget-toolkit",
        source_revision=context.source_revision,
    )
    assert (bundle / "sha256sums.txt").read_bytes() == inventory_before

    assert recover_migrated_bounded_review_cache_entries(
        bundle,
        org_repo="acme/widget-toolkit",
        source_revision=context.source_revision,
    )
    assert verify_sha256sums(bundle)


def test_migrated_packet_cache_recovery_rejects_an_identity_mismatch(tmp_path) -> None:
    bundle = tmp_path / "bundle"
    entry_path, context = _seal_bundle_with_one_packet_cache_entry(bundle)
    inventory_before = (bundle / "sha256sums.txt").read_bytes()

    cached = json.loads(entry_path.read_text(encoding="utf-8"))
    cached["org_repo"] = "someone-else/unrelated-repo"
    entry_path.write_text(json.dumps(cached), encoding="utf-8")

    assert not recover_migrated_bounded_review_cache_entries(
        bundle,
        org_repo="acme/widget-toolkit",
        source_revision=context.source_revision,
    )
    assert (bundle / "sha256sums.txt").read_bytes() == inventory_before


def test_aggregate_grounding_uses_packet_source_identity_for_long_locations() -> None:
    long_location = ";".join(f"repository/path/{index}.py" for index in range(80))
    facts = DEFAULT_FACTS.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={"source": fact.source.model_copy(update={"location": long_location})}
                )
                for fact in DEFAULT_FACTS.facts
            ]
        }
    )
    plan = _plan(
        product_facts=facts,
        document_plan=_build_document_plan(CANDIDATE_TEXT, facts),
        claim_accountability=_build_claim_accountability(
            CANDIDATE_TEXT,
            facts,
            _default_claim_specs(),
        ),
    )

    execution = execute_bounded_review(
        org_repo="acme/widget-toolkit",
        candidate_text=CANDIDATE_TEXT,
        product_facts=facts.model_dump(mode="json"),
        visitor_contract=build_presentation_visitor_contract(
            applicable_h2_headings=_headings(),
            primary_example_language="python",
        ),
        plan=plan,
        coverage_ledger=brp.build_coverage_ledger(
            plan,
            atomic_units=_atomic_units(product_facts=facts),
        ),
        blind_client=_PacketSequenceClient(list(plan.visitor_packets)),
        factual_client=_PacketSequenceClient(list(plan.factual_packets)),
        blind_prompt_id="blind_readme_quality_review",
        factual_prompt_id="factual_readme_plan_review",
    )

    assert execution.aggregate.overall == "ACCEPT"
    assert execution.factual_grounding.valid is True
    factual_locations = {finding.evidence_location for finding in execution.factual_result.findings}
    assert factual_locations
    assert all(location.startswith("fact-source://") for location in factual_locations)


def test_unrelated_global_fact_hash_change_reuses_exact_packets_without_provider_calls(
    tmp_path,
) -> None:
    plan = _plan()
    ledger = brp.build_coverage_ledger(plan, atomic_units=_atomic_units())
    first_context = _cache_context()
    changed_context = first_context.model_copy(
        update={"facts_hash": "1" * 64, "provenance_hash": "2" * 64}
    )
    common = {
        "org_repo": "acme/widget-toolkit",
        "candidate_text": CANDIDATE_TEXT,
        "product_facts": DEFAULT_FACTS.model_dump(mode="json"),
        "visitor_contract": build_presentation_visitor_contract(
            applicable_h2_headings=_headings(),
            primary_example_language="python",
        ),
        "plan": plan,
        "coverage_ledger": ledger,
        "blind_prompt_id": "blind_readme_quality_review",
        "factual_prompt_id": "factual_readme_plan_review",
        "cache_dir": tmp_path / "packet-cache",
    }

    execute_bounded_review(
        **common,
        cache_context=first_context,
        blind_client=_PacketSequenceClient(list(plan.visitor_packets)),
        factual_client=_PacketSequenceClient(list(plan.factual_packets)),
    )
    reused = execute_bounded_review(
        **common,
        cache_context=changed_context,
        blind_client=_FailIfCalledClient(),
        factual_client=_FailIfCalledClient(),
    )

    assert reused.aggregate.overall == "ACCEPT"
    assert sum(
        item.get("context_mode") == "bounded_packet_cache_reuse"
        for item in reused.grounding_history
    ) == len(plan.visitor_packets) + len(plan.factual_packets)


def test_legacy_global_fact_cache_key_is_distinct_and_migratable() -> None:
    packet = _plan().visitor_packets[0]
    context = _cache_context()

    stable = cache_key_for_packet(packet, context, runtime_contract_hash="1" * 64)
    packet_identity = legacy_packet_identity_cache_key_for_packet(
        packet, context, runtime_contract_hash="1" * 64
    )
    legacy = legacy_cache_key_for_packet(packet, context, runtime_contract_hash="1" * 64)

    assert stable != packet_identity
    assert packet_identity != legacy
    assert stable != legacy
    assert stable == cache_key_for_packet(
        packet,
        context.model_copy(update={"facts_hash": "3" * 64, "provenance_hash": "4" * 64}),
        runtime_contract_hash="1" * 64,
    )


def test_stable_cache_identity_ignores_packet_order_id() -> None:
    packet = _plan().visitor_packets[0]
    reordered = packet.model_copy(update={"packet_id": f"pkt-visitor-9999-{packet.packet_sha256}"})
    context = _cache_context()

    assert cache_key_for_packet(packet, context) == cache_key_for_packet(reordered, context)
    assert legacy_packet_identity_cache_key_for_packet(
        packet, context
    ) != legacy_packet_identity_cache_key_for_packet(reordered, context)


def test_stable_cache_receipt_rebinds_changed_packet_id_without_provider_call(tmp_path) -> None:
    plan = _plan()
    packet = plan.visitor_packets[0]
    context = _cache_context()
    cache_dir = tmp_path / "packet-cache"
    execution = execute_bounded_review(
        org_repo="acme/widget-toolkit",
        candidate_text=CANDIDATE_TEXT,
        product_facts=DEFAULT_FACTS.model_dump(mode="json"),
        visitor_contract=build_presentation_visitor_contract(
            applicable_h2_headings=_headings(),
            primary_example_language="python",
        ),
        plan=plan,
        coverage_ledger=brp.build_coverage_ledger(plan, atomic_units=_atomic_units()),
        blind_client=_PacketSequenceClient(list(plan.visitor_packets)),
        factual_client=_PacketSequenceClient(list(plan.factual_packets)),
        blind_prompt_id="blind_readme_quality_review",
        factual_prompt_id="factual_readme_plan_review",
    )
    result = next(item for item in execution.packet_results if item.packet_id == packet.packet_id)
    cache_key = cache_key_for_packet(packet, context)
    write_bounded_review_packet_cache(
        cache_dir,
        cache_key=cache_key,
        org_repo="acme/widget-toolkit",
        context=context,
        packet=packet,
        result=result,
        grounding_history=(),
    )
    reordered = packet.model_copy(
        update={"packet_id": f"pkt-visitor-9999-{packet.packet_sha256[:12]}"}
    )
    rebound_plan = plan.model_copy(
        update={
            "visitor_packets": (reordered, *plan.visitor_packets[1:]),
            "plan_hash": "8" * 64,
        }
    )

    loaded = load_bounded_review_packet_cache(
        cache_dir,
        cache_key=cache_key,
        org_repo="acme/widget-toolkit",
        context=context,
        packet=reordered,
        plan=rebound_plan,
    )

    assert loaded is not None
    assert loaded.packet_id == reordered.packet_id
    assert loaded.result.packet_id == reordered.packet_id
    assert loaded.grounding_history[-1]["reviewed_packet_id"] == packet.packet_id
    assert loaded.grounding_history[-1]["current_packet_id"] == reordered.packet_id


def test_legacy_global_fact_cache_receipt_migrates_without_provider_call(tmp_path) -> None:
    plan = _plan()
    packet = plan.visitor_packets[0]
    context = _cache_context()
    runtime_contract_hash = "1" * 64
    cache_dir = tmp_path / "packet-cache"
    execution = execute_bounded_review(
        org_repo="acme/widget-toolkit",
        candidate_text=CANDIDATE_TEXT,
        product_facts=DEFAULT_FACTS.model_dump(mode="json"),
        visitor_contract=build_presentation_visitor_contract(
            applicable_h2_headings=_headings(),
            primary_example_language="python",
        ),
        plan=plan,
        coverage_ledger=brp.build_coverage_ledger(plan, atomic_units=_atomic_units()),
        blind_client=_PacketSequenceClient(list(plan.visitor_packets)),
        factual_client=_PacketSequenceClient(list(plan.factual_packets)),
        blind_prompt_id="blind_readme_quality_review",
        factual_prompt_id="factual_readme_plan_review",
    )
    result = next(item for item in execution.packet_results if item.packet_id == packet.packet_id)
    legacy_key = legacy_cache_key_for_packet(
        packet,
        context,
        runtime_contract_hash=runtime_contract_hash,
    )
    write_bounded_review_packet_cache(
        cache_dir,
        cache_key=legacy_key,
        org_repo="acme/widget-toolkit",
        context=context,
        packet=packet,
        result=result,
        grounding_history=(),
    )
    reuse_events: list[dict] = []
    cache = BoundedReviewPacketCache(
        org_repo="acme/widget-toolkit",
        plan=plan,
        cache_dir=cache_dir,
        context=context,
        blind_prompt_id="blind_readme_quality_review",
        factual_prompt_id="factual_readme_plan_review",
        record_cache_reuse=lambda **event: reuse_events.append(event),
    )

    loaded = cache.load(
        packet,
        runtime_contract_hash=runtime_contract_hash,
        validate_result=lambda _result: True,
    )

    stable_key = cache_key_for_packet(
        packet,
        context,
        runtime_contract_hash=runtime_contract_hash,
    )
    assert loaded is not None
    assert loaded[0] == result
    assert reuse_events
    assert (cache_dir / f"{legacy_key}.json").is_file()
    assert (cache_dir / f"{stable_key}.json").is_file()
    assert any(
        item.get("context_mode") == "bounded_packet_cache_identity_migration" for item in loaded[1]
    )


def test_cache_entry_validator_can_selectively_reject_stale_retry_evidence(tmp_path) -> None:
    plan = _plan()
    packet = plan.visitor_packets[0]
    context = _cache_context()
    cache_dir = tmp_path / "packet-cache"
    execution = execute_bounded_review(
        org_repo="acme/widget-toolkit",
        candidate_text=CANDIDATE_TEXT,
        product_facts=DEFAULT_FACTS.model_dump(mode="json"),
        visitor_contract=build_presentation_visitor_contract(
            applicable_h2_headings=_headings(),
            primary_example_language="python",
        ),
        plan=plan,
        coverage_ledger=brp.build_coverage_ledger(plan, atomic_units=_atomic_units()),
        blind_client=_PacketSequenceClient(list(plan.visitor_packets)),
        factual_client=_PacketSequenceClient(list(plan.factual_packets)),
        blind_prompt_id="blind_readme_quality_review",
        factual_prompt_id="factual_readme_plan_review",
    )
    result = next(item for item in execution.packet_results if item.packet_id == packet.packet_id)
    runtime_contract_hash = "7" * 64
    cache_key = cache_key_for_packet(
        packet,
        context,
        runtime_contract_hash=runtime_contract_hash,
    )
    write_bounded_review_packet_cache(
        cache_dir,
        cache_key=cache_key,
        org_repo="acme/widget-toolkit",
        context=context,
        packet=packet,
        result=result,
        grounding_history=({"context_mode": "compact_grounding_retry"},),
    )
    reuse_events: list[dict] = []
    cache = BoundedReviewPacketCache(
        org_repo="acme/widget-toolkit",
        plan=plan,
        cache_dir=cache_dir,
        context=context,
        blind_prompt_id="blind_readme_quality_review",
        factual_prompt_id="factual_readme_plan_review",
        record_cache_reuse=lambda **event: reuse_events.append(event),
    )

    loaded = cache.load(
        packet,
        runtime_contract_hash=runtime_contract_hash,
        validate_cache_entry=lambda entry: bool(
            entry.grounding_history[0].get("grounding_retry_context_contract_version")
        ),
    )

    assert loaded is None
    assert reuse_events == []


def test_exact_packets_rebind_to_current_candidate_without_provider_calls(tmp_path) -> None:
    plan = _plan()
    ledger = brp.build_coverage_ledger(plan, atomic_units=_atomic_units())
    cache_dir = tmp_path / "packet-cache"
    context = _cache_context()
    common = {
        "org_repo": "acme/widget-toolkit",
        "candidate_text": CANDIDATE_TEXT,
        "product_facts": DEFAULT_FACTS.model_dump(mode="json"),
        "visitor_contract": build_presentation_visitor_contract(
            applicable_h2_headings=_headings(),
            primary_example_language="python",
        ),
        "blind_prompt_id": "blind_readme_quality_review",
        "factual_prompt_id": "factual_readme_plan_review",
        "cache_dir": cache_dir,
        "cache_context": context,
    }
    execute_bounded_review(
        **common,
        plan=plan,
        coverage_ledger=ledger,
        blind_client=_PacketSequenceClient(list(plan.visitor_packets)),
        factual_client=_PacketSequenceClient(list(plan.factual_packets)),
    )
    stored_before = {path.name: path.read_bytes() for path in cache_dir.glob("*.json")}

    current_candidate_sha256 = "9" * 64
    rebound_plan = plan.model_copy(
        update={
            "candidate_sha256": current_candidate_sha256,
            "plan_hash": "8" * 64,
            "visitor_packets": tuple(
                packet.model_copy(update={"candidate_sha256": current_candidate_sha256})
                for packet in plan.visitor_packets
            ),
            "factual_packets": tuple(
                packet.model_copy(update={"candidate_sha256": current_candidate_sha256})
                for packet in plan.factual_packets
            ),
        }
    )
    rebound_ledger = ledger.model_copy(update={"plan_hash": rebound_plan.plan_hash})
    execution = execute_bounded_review(
        **common,
        plan=rebound_plan,
        coverage_ledger=rebound_ledger,
        blind_client=_FailIfCalledClient(),
        factual_client=_FailIfCalledClient(),
    )

    assert execution.aggregate.overall == "ACCEPT"
    assert {result.candidate_sha256 for result in execution.packet_results} == {
        current_candidate_sha256
    }
    rebound_events = [
        item
        for item in execution.grounding_history
        if item.get("context_mode") == "bounded_packet_candidate_rebind"
    ]
    assert len(rebound_events) == len(plan.visitor_packets) + len(plan.factual_packets)
    assert all(
        item["reviewed_candidate_sha256"] == plan.candidate_sha256
        and item["current_candidate_sha256"] == current_candidate_sha256
        for item in rebound_events
    )
    assert stored_before == {path.name: path.read_bytes() for path in cache_dir.glob("*.json")}


def test_visitor_packets_expose_only_target_anchors_as_finding_evidence() -> None:
    class InspectingClient(_PacketSequenceClient):
        def analyze(self, messages):
            packet = self._packets[self.calls]
            content = "\n".join(str(message.get("content", "")) for message in messages)
            target_anchor_ids = {
                anchor.anchor_id for anchor in build_candidate_review_anchors(packet.section_text)
            }
            neighbor_text = packet.neighbor_context_before + packet.neighbor_context_after
            neighbor_anchor_ids = {
                anchor.anchor_id for anchor in build_candidate_review_anchors(neighbor_text)
            }
            assert target_anchor_ids
            assert target_anchor_ids.issubset(
                {anchor for anchor in target_anchor_ids if anchor in content}
            )
            assert not any(anchor in content for anchor in neighbor_anchor_ids - target_anchor_ids)
            assert '"mode":"target_section_only"' in content
            assert '"applicable_criteria"' in content
            assert '"applicable_mechanical_check_ids"' in content
            return super().analyze(messages)

    plan = _plan()
    ledger = brp.build_coverage_ledger(plan, atomic_units=_atomic_units())

    execution = execute_bounded_review(
        org_repo="acme/widget-toolkit",
        candidate_text=CANDIDATE_TEXT,
        product_facts=DEFAULT_FACTS.model_dump(mode="json"),
        visitor_contract=build_presentation_visitor_contract(
            applicable_h2_headings=_headings(),
            primary_example_language="python",
        ),
        plan=plan,
        coverage_ledger=ledger,
        blind_client=InspectingClient(list(plan.visitor_packets)),
        factual_client=_PacketSequenceClient(list(plan.factual_packets)),
        blind_prompt_id="blind_readme_quality_review",
        factual_prompt_id="factual_readme_plan_review",
    )

    assert execution.aggregate.overall == "ACCEPT"


def test_additional_example_packet_cannot_review_global_navigation_or_header_checks() -> None:
    scope = bounded_visitor_scope(
        "additional-examples/convert-a-model",
        neighbor_context_before="## Additional Examples\n",
        neighbor_context_after="## API Reference\n",
    )
    packet = _plan().visitor_packets[0]
    finding = _accept_finding(packet).model_copy(
        update={
            "criterion": "navigation",
            "mechanical_check_id": "header.badge_rows",
            "reported_observed_value": 0,
        }
    )

    errors = bounded_visitor_scope_errors(
        [finding],
        applicable_criteria=frozenset(scope["applicable_criteria"]),
        applicable_mechanical_check_ids=frozenset(scope["applicable_mechanical_check_ids"]),
    )

    assert "navigation is outside bounded scope" in errors[0]
    assert "header.badge_rows is outside bounded scope" in errors[1]


def test_additional_example_packet_receives_only_section_applicable_standards() -> None:
    contract = build_presentation_visitor_contract(
        applicable_h2_headings=_headings(),
        primary_example_language="python",
    )

    projected = bounded_visitor_contract(
        contract,
        "additional-examples/convert-a-model",
    )

    standard_ids = {item["standard_id"] for item in projected["configured_standards"]}
    assert standard_ids == {
        "readme.no_comments",
        "readme.primary_example",
        "readme.public_language",
    }
    primary_example = next(
        item
        for item in projected["configured_standards"]
        if item["standard_id"] == "readme.primary_example"
    )
    assert set(primary_example["parameters"]) == {
        "secondary_examples",
        "secondary_examples_intro",
        "public_internal_assurance",
        "duplicate_generic_headings",
    }
    assert "readme.header" not in standard_ids
    assert "readme.navigation" not in standard_ids
    assert "readme.at_a_glance_mermaid" not in standard_ids


def test_section_packets_receive_complete_candidate_structural_standards() -> None:
    contract = build_presentation_visitor_contract(
        applicable_h2_headings=_headings(),
        primary_example_language="python",
    )

    capabilities = bounded_visitor_contract(contract, "key-capabilities")
    api_reference = bounded_visitor_contract(contract, "api-reference")

    assert {item["standard_id"] for item in capabilities["configured_standards"]} == {
        "readme.key_capabilities",
        "readme.no_comments",
        "readme.public_language",
    }
    assert {item["standard_id"] for item in api_reference["configured_standards"]} == {
        "readme.api_reference",
        "readme.no_comments",
        "readme.public_language",
    }


def test_development_commands_may_be_assessed_for_example_presentation() -> None:
    scope = bounded_visitor_scope(
        "development-and-testing/focused-commands-and-repository-scripts",
        neighbor_context_before="### Tests\n",
        neighbor_context_after="## License\n",
    )

    assert "example_presentation" in scope["applicable_criteria"]


def test_runtime_authority_invalidates_visitor_and_factual_packet_cache_identity() -> None:
    plan = _plan()
    context = _cache_context()
    visitor = plan.visitor_packets[0]
    factual = plan.factual_packets[0]

    visitor_before = cache_key_for_packet(
        visitor,
        context,
        runtime_contract_hash="1" * 64,
    )
    visitor_after = cache_key_for_packet(
        visitor,
        context,
        runtime_contract_hash="2" * 64,
    )
    factual_before = cache_key_for_packet(
        factual,
        context,
        runtime_contract_hash="1" * 64,
    )
    factual_after = cache_key_for_packet(
        factual,
        context,
        runtime_contract_hash="2" * 64,
    )

    assert visitor_before != visitor_after
    assert factual_before != factual_after


def test_factual_cache_hit_is_regrounded_before_reuse(tmp_path) -> None:
    plan = _plan()
    ledger = brp.build_coverage_ledger(plan, atomic_units=_atomic_units())
    cache_dir = tmp_path / "packet-cache"
    arguments = {
        "org_repo": "acme/widget-toolkit",
        "candidate_text": CANDIDATE_TEXT,
        "product_facts": DEFAULT_FACTS.model_dump(mode="json"),
        "visitor_contract": build_presentation_visitor_contract(
            applicable_h2_headings=_headings(),
            primary_example_language="python",
        ),
        "plan": plan,
        "coverage_ledger": ledger,
        "blind_prompt_id": "blind_readme_quality_review",
        "factual_prompt_id": "factual_readme_plan_review",
        "cache_dir": cache_dir,
        "cache_context": _cache_context(),
    }
    execute_bounded_review(
        **arguments,
        blind_client=_PacketSequenceClient(list(plan.visitor_packets)),
        factual_client=_PacketSequenceClient(list(plan.factual_packets)),
    )
    factual_cache = next(
        path
        for path in cache_dir.glob("*.json")
        if (
            (loaded := json.loads(path.read_text(encoding="utf-8")))["facet"] == "factual"
            and all(
                item.get("context_mode") != "deterministic_structural_heading_grounding"
                for item in loaded["grounding_history"]
            )
        )
    )
    payload = json.loads(factual_cache.read_text(encoding="utf-8"))
    payload["result"]["findings"][0]["fact_id"] = "fact.not-selected"
    payload["result_sha256"] = _canonical_hash(payload["result"])
    factual_cache.write_text(json.dumps(payload), encoding="utf-8")

    packet = next(item for item in plan.factual_packets if item.packet_id == payload["packet_id"])
    factual_client = _PacketSequenceClient([packet])
    result = execute_bounded_review(
        **arguments,
        blind_client=_FailIfCalledClient(),
        factual_client=factual_client,
    )

    assert result.aggregate.overall == "ACCEPT"
    assert factual_client.calls == 1


def test_successful_packets_survive_one_parallel_packet_failure(tmp_path) -> None:
    class MatchingClient:
        def __init__(self, packets, *, fail_packet_id=None):
            self._packets = tuple(packets)
            self._fail_packet_id = fail_packet_id
            self.calls = 0

        def analyze(self, messages):
            content = "\n".join(str(message.get("content", "")) for message in messages)
            packet = next(
                packet
                for packet in self._packets
                if any(
                    anchor.anchor_id in content
                    for anchor in build_candidate_review_anchors(
                        packet.section_text
                        if isinstance(packet, brp.BoundedVisitorPacketV1)
                        else packet.unit_text
                    )
                )
            )
            self.calls += 1
            if packet.packet_id == self._fail_packet_id:
                raise RuntimeError("forced packet-local transport failure")
            finding = _accept_finding(packet).model_copy(update={"section": packet.section_path})
            return AnalysisResult(
                parsed={
                    "verdict": "ACCEPT",
                    "reasoning": f"Packet {packet.packet_id} is accepted.",
                    "failed_criteria": [],
                    "sections_affected": [],
                    "required_repair": "",
                    "findings": [finding.model_dump(mode="json")],
                },
                meta=LLMResponseMeta(),
            )

    plan = _plan()
    ledger = brp.build_coverage_ledger(plan, atomic_units=_atomic_units())
    failed_packet = plan.visitor_packets[0]
    cache_dir = tmp_path / "packet-cache"
    common = {
        "org_repo": "acme/widget-toolkit",
        "candidate_text": CANDIDATE_TEXT,
        "product_facts": DEFAULT_FACTS.model_dump(mode="json"),
        "visitor_contract": build_presentation_visitor_contract(
            applicable_h2_headings=_headings(),
            primary_example_language="python",
        ),
        "plan": plan,
        "coverage_ledger": ledger,
        "blind_prompt_id": "blind_readme_quality_review",
        "factual_prompt_id": "factual_readme_plan_review",
        "max_workers": 4,
        "cache_dir": cache_dir,
        "cache_context": _cache_context(),
    }

    with pytest.raises(RuntimeError, match="forced packet-local transport failure"):
        execute_bounded_review(
            **common,
            blind_client=MatchingClient(
                plan.visitor_packets,
                fail_packet_id=failed_packet.packet_id,
            ),
            factual_client=MatchingClient(plan.factual_packets),
        )

    retry_blind = MatchingClient(plan.visitor_packets)
    retry_factual = MatchingClient(plan.factual_packets)
    execution = execute_bounded_review(
        **common,
        blind_client=retry_blind,
        factual_client=retry_factual,
    )

    assert execution.aggregate.overall == "ACCEPT"
    assert retry_blind.calls == 1
    assert retry_factual.calls == 0
