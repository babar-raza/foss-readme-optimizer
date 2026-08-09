"""Project source assurance against exact fact-slot candidate ownership."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_source_claim_obligations import (
    accepted_obligation_bindings,
)
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.source_claim_assurance import SourceClaimAssurance
from readme_agent.readme.source_claim_fact_binding import complete_source_claim_fact_binding
from readme_agent.readme.source_claim_risk import (
    classify_source_claim_risk,
    obligation_requires_source_entailment,
)


def project_source_assurance_for_candidate(
    source_text: str,
    assessment: ReadmeAssessmentV1,
    assurance: SourceClaimAssurance,
    provenance: list[CandidateContentProvenanceV1],
    facts: ProductFactsV2,
    candidate_text: str = "",
) -> SourceClaimAssurance:
    """Recompile inherited detail only after exact canonical coordinates cover it."""

    claims_by_range = {
        (claim.source_byte_start, claim.source_byte_end): claim
        for claim in assessment.material_claims
    }
    replacement_ranges: set[tuple[int, int]] = set()
    for span in assurance.preserve_ranges:
        claim = claims_by_range.get(span)
        if claim is None:
            continue
        risk = classify_source_claim_risk(source_text, claim)
        obligation = risk.obligation_id
        if obligation is None or not obligation_requires_source_entailment(obligation):
            continue
        exact = complete_source_claim_fact_binding(source_text, claim, facts)
        if exact is None:
            continue
        accepted = accepted_obligation_bindings(
            obligation,
            facts,
            provenance,
            exact_source_fact_ids=sorted(exact.fact_ids),
            exact_source_fact_coordinates=list(exact.fact_coordinates),
        )
        if accepted is not None:
            replacement_ranges.add(span)
    del candidate_text
    if not replacement_ranges:
        return assurance
    preserve = sorted(set(assurance.preserve_ranges) - replacement_ranges)
    correction = sorted({*assurance.correction_ranges, *replacement_ranges})
    return SourceClaimAssurance(
        preserve_ranges=preserve,
        correction_ranges=correction,
        fact_authorized_claim_count=len(preserve),
        correction_candidate_count=len(correction),
    )


__all__ = ["project_source_assurance_for_candidate"]
