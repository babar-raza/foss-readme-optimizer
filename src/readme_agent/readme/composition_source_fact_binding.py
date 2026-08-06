"""Bind exact source lineage to pre-existing candidate fact authority."""

from __future__ import annotations

from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.composition_lineage_models import ExactSourcePlacementV1
from readme_agent.readme.document_plan import CandidateContentProvenanceV1


def exact_source_fact_binding_placement(
    binding: CandidateContentProvenanceV1,
    placements: list[ExactSourcePlacementV1],
) -> ExactSourcePlacementV1 | None:
    """Return the one source placement eligible to retain an exact fact binding.

    Byte origin and factual authority are independent. A pre-existing fact binding may
    accompany exact source lineage only when its complete candidate span is contained by
    one governed exact-equivalence placement. Partial, broad, multi-placement, and
    configured-standard-only overlaps are rejected rather than silently widened.
    """

    if binding.authority_scope == "lineage_only":
        return None
    overlaps = [
        placement
        for placement in placements
        if binding.candidate_byte_start < placement.final_byte_end
        and placement.final_byte_start < binding.candidate_byte_end
    ]
    if not overlaps:
        return None
    if (
        len(overlaps) != 1
        or overlaps[0].placement_basis
        not in {"structural_exact_equivalence", "relocated_exact_equivalence"}
        or binding.candidate_byte_start < overlaps[0].final_byte_start
        or overlaps[0].final_byte_end < binding.candidate_byte_end
        or not binding.fact_ids
    ):
        raise ValueError(
            "source placement overlaps generated provenance with an unsupported "
            f"exact-source binding: {binding.provenance_id}"
        )
    return overlaps[0]


def _complete_candidate_provenance(
    start: int,
    end: int,
    candidate_text: str,
    provenance: list[CandidateContentProvenanceV1],
) -> list[CandidateContentProvenanceV1]:
    bindings = [
        binding
        for binding in provenance
        if binding.candidate_byte_start < end and start < binding.candidate_byte_end
    ]
    if not bindings:
        return []
    claim_bytes = candidate_text.encode("utf-8")[start:end]
    covered = bytearray(len(claim_bytes))
    for binding in bindings:
        relative_start = max(binding.candidate_byte_start, start) - start
        relative_end = min(binding.candidate_byte_end, end) - start
        covered[relative_start:relative_end] = b"\x01" * (relative_end - relative_start)
    uncovered = bytes(byte for index, byte in enumerate(claim_bytes) if not covered[index])
    return bindings if not uncovered.strip() else []


def exact_source_claim_provenance(
    claim: ReadmeMaterialClaimAssessmentV1,
    source_text: str,
    candidate_text: str,
    provenance: list[CandidateContentProvenanceV1],
    placements: list[ExactSourcePlacementV1],
) -> list[CandidateContentProvenanceV1]:
    """Map one exact source-owned claim to its complete candidate fact binding."""

    owned = [placement for placement in placements if placement.source_owner_id == claim.claim_id]
    if not owned:
        return []
    if len(owned) != 1:
        return []
    placement = owned[0]
    if (
        placement.source_byte_start != claim.source_byte_start
        or placement.source_byte_end != claim.source_byte_end
    ):
        raise ValueError(f"source claim placement is partial: {claim.claim_id}")
    source = source_text.encode("utf-8")
    candidate = candidate_text.encode("utf-8")
    source_bytes = source[claim.source_byte_start : claim.source_byte_end]
    candidate_bytes = candidate[placement.final_byte_start : placement.final_byte_end]
    if source_bytes != candidate_bytes:
        raise ValueError(f"source claim placement changed exact bytes: {claim.claim_id}")
    bindings = _complete_candidate_provenance(
        placement.final_byte_start,
        placement.final_byte_end,
        candidate_text,
        provenance,
    )
    if any(
        binding.candidate_byte_start < placement.final_byte_start
        or placement.final_byte_end < binding.candidate_byte_end
        for binding in bindings
    ):
        raise ValueError(f"source claim has broad candidate provenance: {claim.claim_id}")
    return bindings
