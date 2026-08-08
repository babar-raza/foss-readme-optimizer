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
    candidate_text: str = "",
) -> SourceClaimAssurance:
    """Recompile source claims only when the canonical fact-bound slot covers their meaning."""

    api_slot_ready = any(
        binding.provenance_id.startswith("template.section.api_reference")
        and binding.fact_ids
        and binding.candidate_byte_end > binding.candidate_byte_start
        for binding in provenance
    )
    claims_by_range = {
        (claim.source_byte_start, claim.source_byte_end): claim
        for claim in assessment.material_claims
    }
    replacement_ranges = {
        span
        for span in assurance.preserve_ranges
        if (claim := claims_by_range.get(span)) is not None
        and api_slot_ready
        and classify_source_claim_risk(source_text, claim).obligation_id == "api_public_surface"
    }
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
