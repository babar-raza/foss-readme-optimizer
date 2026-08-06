"""Project source assurance against exact fact-slot candidate ownership."""

from __future__ import annotations

from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.source_claim_assurance import SourceClaimAssurance
from readme_agent.readme.source_claim_risk import classify_source_claim_risk


def project_source_assurance_for_candidate(
    source_text: str,
    assessment: ReadmeAssessmentV1,
    assurance: SourceClaimAssurance,
    provenance: list[CandidateContentProvenanceV1],
) -> SourceClaimAssurance:
    """Recompile API claims only when an exact fact-bound candidate API slot exists."""

    api_slot_ready = any(
        binding.provenance_id.startswith("template.section.api_reference")
        and binding.fact_ids
        and binding.candidate_byte_end > binding.candidate_byte_start
        for binding in provenance
    )
    if not api_slot_ready:
        return assurance
    claims_by_range = {
        (claim.source_byte_start, claim.source_byte_end): claim
        for claim in assessment.material_claims
    }
    api_ranges = {
        span
        for span in assurance.preserve_ranges
        if (claim := claims_by_range.get(span)) is not None
        and classify_source_claim_risk(source_text, claim).obligation_id == "api_public_surface"
    }
    if not api_ranges:
        return assurance
    preserve = sorted(set(assurance.preserve_ranges) - api_ranges)
    correction = sorted({*assurance.correction_ranges, *api_ranges})
    return SourceClaimAssurance(
        preserve_ranges=preserve,
        correction_ranges=correction,
        fact_authorized_claim_count=len(preserve),
        correction_candidate_count=len(correction),
    )


__all__ = ["project_source_assurance_for_candidate"]
