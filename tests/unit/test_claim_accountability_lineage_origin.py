"""Prove claim origin and survival follow exact composition lineage when available."""

from __future__ import annotations

import hashlib

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.readme.claim_accountability import build_readme_claim_accountability_map
from readme_agent.readme.claim_map import ReadmeClaimMapV1
from readme_agent.readme.composition_lineage_models import (
    ExactSourcePlacementV1,
    ReadmeCompositionLedgerV1,
)

CLAIM = "Repeated capability text.\n"


def _facts() -> ProductFactsV2:
    return ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))


def _placement(
    source: str,
    candidate: str,
    *,
    source_start: int,
    candidate_start: int,
    length: int,
) -> ExactSourcePlacementV1:
    source_content = source.encode("utf-8")[source_start : source_start + length]
    candidate_content = candidate.encode("utf-8")[candidate_start : candidate_start + length]
    assert source_content == candidate_content
    digest = hashlib.sha256(source_content).hexdigest()
    return ExactSourcePlacementV1(
        placement_id=f"test.placement.{source_start}.{candidate_start}.{length}",
        placement_basis="operation_unchanged_exact",
        source_byte_start=source_start,
        source_byte_end=source_start + length,
        source_content_sha256=digest,
        final_byte_start=candidate_start,
        final_byte_end=candidate_start + length,
        final_content_sha256=digest,
    )


def _ledger(
    source: str,
    candidate: str,
    placements: list[ExactSourcePlacementV1],
) -> ReadmeCompositionLedgerV1:
    source_bytes = source.encode("utf-8")
    candidate_bytes = candidate.encode("utf-8")
    return ReadmeCompositionLedgerV1.model_construct(
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        source_bytes=len(source_bytes),
        candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        candidate_bytes=len(candidate_bytes),
        operation_reconstruction_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        source_placements=placements,
        candidate_provenance=[],
        segments=[],
    )


def _accountability(
    source: str,
    candidate: str,
    ledger: ReadmeCompositionLedgerV1 | None,
):
    facts = _facts()
    claim_map = ReadmeClaimMapV1(
        org_repo=facts.org_repo,
        facts_hash=facts.canonical_hash(),
        candidate_sha256=hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
        claims=[],
    )
    return build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=source,
        candidate_text=candidate,
        facts=facts,
        generated_claim_map=claim_map,
        composition_ledger=ledger,
    )


def _stage_records(accountability, stage: str):
    return sorted(
        (record for record in accountability.claims if record.stage == stage),
        key=lambda record: record.source_byte_start,
    )


def test_duplicate_text_cannot_spoof_candidate_origin_when_ledger_maps_second_copy() -> None:
    source = f"# Source\n\n{CLAIM}"
    candidate = f"# Candidate\n\n{CLAIM}\n{CLAIM}"
    source_start = source.index(CLAIM)
    first_candidate_start = candidate.index(CLAIM)
    second_candidate_start = candidate.index(CLAIM, first_candidate_start + 1)
    placement = _placement(
        source,
        candidate,
        source_start=source_start,
        candidate_start=second_candidate_start,
        length=len(CLAIM.encode("utf-8")),
    )

    accountability = _accountability(source, candidate, _ledger(source, candidate, [placement]))

    assert [record.origin for record in _stage_records(accountability, "candidate")] == [
        "generated",
        "inherited",
    ]
    assert _stage_records(accountability, "source")[0].survives_in_candidate is True


def test_partial_placement_does_not_claim_complete_candidate_or_source_claim() -> None:
    source = f"# Source\n\n{CLAIM}"
    candidate = f"# Candidate\n\n{CLAIM}"
    source_start = source.index(CLAIM)
    candidate_start = candidate.index(CLAIM)
    partial_length = len(b"Repeated")
    placement = _placement(
        source,
        candidate,
        source_start=source_start,
        candidate_start=candidate_start,
        length=partial_length,
    )

    accountability = _accountability(source, candidate, _ledger(source, candidate, [placement]))

    assert _stage_records(accountability, "candidate")[0].origin == "generated"
    assert _stage_records(accountability, "source")[0].survives_in_candidate is False


def test_exact_placement_owns_complete_candidate_origin_and_source_survival() -> None:
    source = f"# Source\n\n{CLAIM}"
    candidate = f"# Candidate\n\n{CLAIM}"
    source_start = source.index(CLAIM)
    candidate_start = candidate.index(CLAIM)
    placement = _placement(
        source,
        candidate,
        source_start=source_start,
        candidate_start=candidate_start,
        length=len(CLAIM.encode("utf-8")),
    )

    accountability = _accountability(source, candidate, _ledger(source, candidate, [placement]))

    assert _stage_records(accountability, "candidate")[0].origin == "inherited"
    assert _stage_records(accountability, "source")[0].survives_in_candidate is True


def test_no_ledger_retains_legacy_text_count_compatibility() -> None:
    source = f"# Source\n\n{CLAIM}"
    candidate = f"# Candidate\n\n{CLAIM}\n{CLAIM}"

    accountability = _accountability(source, candidate, None)

    assert [record.origin for record in _stage_records(accountability, "candidate")] == [
        "inherited",
        "generated",
    ]
    assert _stage_records(accountability, "source")[0].survives_in_candidate is True
