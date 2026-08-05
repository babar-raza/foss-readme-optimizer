"""Exact-source lineage and fact-authority coexistence controls."""

from __future__ import annotations

import hashlib

import pytest

from readme_agent.presentation.verified_source_placements import (
    exclude_source_placements_from_provenance,
)
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.composition_lineage import build_composition_ledger
from readme_agent.readme.composition_lineage_models import ExactSourcePlacementV1
from readme_agent.readme.composition_operation_origins import (
    legacy_operation_provenance,
    replay_operation_origins,
)
from readme_agent.readme.composition_source_fact_binding import exact_source_claim_provenance
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import CandidateContentProvenanceV1


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fixture() -> tuple[
    str,
    str,
    ExactSourcePlacementV1,
    CandidateContentProvenanceV1,
]:
    source = "# Old\n\nExact fact summary.\n"
    candidate = "# New\n\nExact fact summary.\n\nGenerated detail.\n"
    source_start = source.index("Exact fact summary.")
    final_start = candidate.index("Exact fact summary.")
    exact = b"Exact fact summary.\n"
    placement = ExactSourcePlacementV1(
        placement_id="source.structural-claim.0000",
        placement_basis="structural_exact_equivalence",
        source_owner_id="claim.summary",
        structural_role="opening_material_claim",
        source_byte_start=source_start,
        source_byte_end=source_start + len(exact),
        source_content_sha256=_sha256(exact),
        final_byte_start=final_start,
        final_byte_end=final_start + len(exact),
        final_content_sha256=_sha256(exact),
    )
    binding = CandidateContentProvenanceV1(
        provenance_id="template.summary",
        candidate_byte_start=final_start,
        candidate_byte_end=final_start + len(exact),
        fact_ids=["product.summary:verified"],
        rationale="Bind the exact generated summary to one accepted fact.",
    )
    return source, candidate, placement, binding


def _operation_provenance(source: str, candidate: str):
    operation = build_operation(
        operation_id="readme.exact-source-fact-binding",
        operation="replace",
        source=source.encode("utf-8"),
        start=0,
        end=len(source.encode("utf-8")),
        replacement=candidate,
        fact_ids=[],
        treatment="presentation_policy_correction",
        rationale="Exercise exact source adoption inside a compiled replacement.",
    )
    lineage = legacy_operation_provenance(
        replay_operation_origins(source.encode("utf-8"), [operation])
    )
    return operation, lineage


def test_exact_structural_source_keeps_only_its_existing_fact_binding() -> None:
    source, candidate, placement, binding = _fixture()
    operation, operation_provenance = _operation_provenance(source, candidate)

    retained = [
        *exclude_source_placements_from_provenance([binding], [placement]),
        *operation_provenance,
    ]
    ledger = build_composition_ledger(
        source,
        candidate,
        [operation],
        retained,
        [placement],
    )

    assert binding in retained
    bound_segments = [
        segment for segment in ledger.segments if binding.provenance_id in segment.provenance_ids
    ]
    assert len(bound_segments) == 1
    assert bound_segments[0].origin == "source_preserved"
    assert bound_segments[0].authority == "source_exact_fact_bound"
    assert bound_segments[0].fact_ids == binding.fact_ids
    assert bound_segments[0].content_text == "Exact fact summary.\n"
    assert ledger.candidate_sha256 == _sha256(candidate.encode("utf-8"))


@pytest.mark.parametrize("span_kind", ["partial", "broad", "configured_only"])
def test_source_fact_binding_rejects_partial_broad_or_factless_authority(
    span_kind: str,
) -> None:
    _, _candidate, placement, binding = _fixture()
    start = binding.candidate_byte_start
    end = binding.candidate_byte_end
    fact_ids = binding.fact_ids
    configured_standard_ids: list[str] = []
    if span_kind == "partial":
        start += 1
        end += 1
    elif span_kind == "broad":
        start -= 1
        end += 1
    else:
        fact_ids = []
        configured_standard_ids = ["readme.presentation.summary"]
    unsafe = binding.model_copy(
        update={
            "provenance_id": f"template.summary.{span_kind}",
            "candidate_byte_start": start,
            "candidate_byte_end": end,
            "fact_ids": fact_ids,
            "configured_standard_ids": configured_standard_ids,
        }
    )

    with pytest.raises(ValueError, match="unsupported exact-source binding"):
        exclude_source_placements_from_provenance([unsafe], [placement])


def test_arbitrary_source_without_prior_provenance_remains_source_exact_only() -> None:
    source, candidate, placement, _ = _fixture()
    operation, operation_provenance = _operation_provenance(source, candidate)
    retained = operation_provenance

    ledger = build_composition_ledger(
        source,
        candidate,
        [operation],
        retained,
        [placement],
    )
    source_segments = [
        segment for segment in ledger.segments if segment.origin == "source_preserved"
    ]

    assert source_segments
    assert all(segment.authority == "source_exact" for segment in source_segments)
    assert all(not segment.fact_ids and not segment.provenance_ids for segment in source_segments)


def test_policy_split_source_claim_receives_no_implicit_fact_binding() -> None:
    source, candidate, placement, binding = _fixture()
    claim = next(
        item
        for item in assess_material_claims(source)
        if item.source_byte_start == placement.source_byte_start
        and item.source_byte_end == placement.source_byte_end
    )
    split_at = placement.source_byte_start + 6
    final_split_at = placement.final_byte_start + 6
    source_bytes = source.encode("utf-8")
    candidate_bytes = candidate.encode("utf-8")
    prefix = source_bytes[placement.source_byte_start : split_at]
    suffix = source_bytes[split_at : placement.source_byte_end]
    split_placements = [
        ExactSourcePlacementV1(
            placement_id="source.policy-prefix",
            placement_basis="composer_inserted_exact",
            source_owner_id=claim.claim_id,
            source_byte_start=placement.source_byte_start,
            source_byte_end=split_at,
            source_content_sha256=_sha256(prefix),
            final_byte_start=placement.final_byte_start,
            final_byte_end=final_split_at,
            final_content_sha256=_sha256(
                candidate_bytes[placement.final_byte_start : final_split_at]
            ),
        ),
        ExactSourcePlacementV1(
            placement_id="source.policy-suffix",
            placement_basis="composer_inserted_exact",
            source_owner_id=claim.claim_id,
            source_byte_start=split_at,
            source_byte_end=placement.source_byte_end,
            source_content_sha256=_sha256(suffix),
            final_byte_start=final_split_at,
            final_byte_end=placement.final_byte_end,
            final_content_sha256=_sha256(
                candidate_bytes[final_split_at : placement.final_byte_end]
            ),
        ),
    ]

    assert (
        exact_source_claim_provenance(
            claim,
            source,
            candidate,
            [binding],
            split_placements,
        )
        == []
    )


def test_partial_unique_source_claim_placement_remains_rejected() -> None:
    source, candidate, placement, binding = _fixture()
    claim = next(
        item
        for item in assess_material_claims(source)
        if item.source_byte_start == placement.source_byte_start
        and item.source_byte_end == placement.source_byte_end
    )
    partial_bytes = source.encode("utf-8")[
        placement.source_byte_start : placement.source_byte_end - 1
    ]
    partial = placement.model_copy(
        update={
            "source_owner_id": claim.claim_id,
            "source_byte_end": placement.source_byte_end - 1,
            "source_content_sha256": _sha256(partial_bytes),
            "final_byte_end": placement.final_byte_end - 1,
            "final_content_sha256": _sha256(partial_bytes),
        }
    )

    with pytest.raises(ValueError, match="source claim placement is partial"):
        exact_source_claim_provenance(
            claim,
            source,
            candidate,
            [binding],
            [partial],
        )
