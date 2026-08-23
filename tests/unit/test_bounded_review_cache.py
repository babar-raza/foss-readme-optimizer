"""Bounded review reuses only exact validated packet results."""

from __future__ import annotations

import pytest
from bounded_review_result_support import _accept_finding
from bounded_review_test_support import (
    CANDIDATE_TEXT,
    DEFAULT_FACTS,
    _atomic_units,
    _FailIfCalledClient,
    _PacketSequenceClient,
    _plan,
)

from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.presentation.visitor_contract import build_presentation_visitor_contract
from readme_agent.specialists import bounded_review_packets as brp
from readme_agent.specialists.bounded_review_cache import BoundedReviewCacheContextV1
from readme_agent.specialists.bounded_review_execution import execute_bounded_review
from readme_agent.specialists.bounded_review_visitor_scope import (
    bounded_visitor_scope,
    bounded_visitor_scope_errors,
)
from readme_agent.specialists.review_candidate_anchors import build_candidate_review_anchors


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
