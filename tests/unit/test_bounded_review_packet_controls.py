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
import pathlib

import pytest
from bounded_review_test_support import (
    DEFAULT_CLAIM_ACCOUNTABILITY,
    _build_product_facts,
    _plan,
)
from pydantic import ValidationError

from readme_agent.specialists import bounded_review_packets as brp
from readme_agent.specialists.review_finding_grounding import GroundedReviewFindingV1


def test_module_never_calls_a_provider() -> None:
    forbidden_markers = ("llm", "reviewer_client", "ForcedToolClient", "capabilities.dispatcher")
    module_dir = pathlib.Path(brp.__file__).parent
    for source_path in sorted(module_dir.glob("bounded_review_*.py")):
        if source_path.name == "bounded_review_execution.py":
            continue  # the separate execution seam intentionally invokes registered role clients
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
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
                    f"forbidden provider-adjacent import found in {source_path.name}: {name!r}"
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
