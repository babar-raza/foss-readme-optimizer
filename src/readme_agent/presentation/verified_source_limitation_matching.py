"""Match inherited limitations to fact-bound canonical limitation rows."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.limitation_semantics import public_limitations_equivalent

_LIMITATION_PROVENANCE = "template.section.scope_and_limitations.claim:"


def fact_bound_limitation_candidate_claims(
    source_claim_text: str,
    candidate_bytes: bytes,
    candidate_claims: list[ReadmeMaterialClaimAssessmentV1],
    facts: ProductFactsV2,
    provenance: list[CandidateContentProvenanceV1],
) -> list[ReadmeMaterialClaimAssessmentV1]:
    """Find the one canonical limitation row that subsumes inherited wording."""

    limitation_fact_id = facts.selected_fact_ids.get("product.limitations")
    if limitation_fact_id is None:
        return []
    bindings_by_range: dict[tuple[int, int], list[CandidateContentProvenanceV1]] = {}
    for binding in provenance:
        if not binding.provenance_id.startswith(_LIMITATION_PROVENANCE):
            continue
        if limitation_fact_id not in binding.fact_ids:
            continue
        if not any(
            coordinate.fact_id == limitation_fact_id and coordinate.field == "product.limitations"
            for coordinate in binding.fact_coordinates
        ):
            continue
        bindings_by_range.setdefault(
            (binding.candidate_byte_start, binding.candidate_byte_end), []
        ).append(binding)

    matches: list[ReadmeMaterialClaimAssessmentV1] = []
    for claim in candidate_claims:
        bindings = bindings_by_range.get((claim.source_byte_start, claim.source_byte_end), [])
        if len(bindings) != 1:
            continue
        candidate_text = candidate_bytes[claim.source_byte_start : claim.source_byte_end].decode(
            "utf-8"
        )
        if public_limitations_equivalent(source_claim_text, candidate_text):
            matches.append(claim)
    return matches


__all__ = ["fact_bound_limitation_candidate_claims"]
