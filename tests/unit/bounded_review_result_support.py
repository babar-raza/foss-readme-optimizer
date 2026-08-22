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

from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.specialists import bounded_review_packets as brp
from readme_agent.specialists.review_finding_grounding import GroundedReviewFindingV1


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


class _PacketSequenceClient:
    def __init__(self, packets: list[brp.BoundedPacketV1]) -> None:
        self._packets = packets
        self.calls = 0

    def analyze(self, messages: list[dict]) -> AnalysisResult:
        packet = self._packets[self.calls]
        self.calls += 1
        finding = _accept_finding(packet).model_copy(update={"section": packet.section_path})
        return AnalysisResult(
            parsed={
                "verdict": "ACCEPT",
                "reasoning": f"Packet {packet.packet_id} is grounded and visitor-ready.",
                "failed_criteria": [],
                "sections_affected": [],
                "required_repair": "",
                "findings": [finding.model_dump(mode="json")],
            },
            meta=LLMResponseMeta(),
        )


class _FailIfCalledClient:
    def analyze(self, messages: list[dict]) -> AnalysisResult:
        raise AssertionError("oversized invalid contracts must fail before any reviewer call")


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
