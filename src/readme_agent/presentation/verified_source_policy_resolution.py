"""Build exact partial source-claim resolutions for verified policy corrections."""

from __future__ import annotations

from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.document_plan import SourceClaimResolutionV1
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1


def source_policy_resolution(
    claim: ReadmeMaterialClaimAssessmentV1,
    corrections: list[SourceClaimPolicyCorrectionV1],
) -> SourceClaimResolutionV1 | None:
    """Bind policy spans overlapping one material claim without claiming its other bytes."""

    owned = [
        correction
        for correction in corrections
        if claim.source_byte_start < correction.source_byte_end
        and correction.source_byte_start < claim.source_byte_end
    ]
    if not owned:
        return None
    return SourceClaimResolutionV1(
        claim_id=claim.claim_id,
        source_byte_start=claim.source_byte_start,
        source_byte_end=claim.source_byte_end,
        content_sha256=claim.content_sha256,
        resolution="presentation_policy_correction",
        policy_corrections=owned,
        evidence=[
            f"source-claim:{claim.claim_id}",
            f"source-content-sha256:{claim.content_sha256}",
            *(f"policy-correction:{correction.correction_id}" for correction in owned),
        ],
        rationale=(
            "Apply exact visitor-policy corrections inside the claim while retaining all "
            "unaffected bytes under source-exact lineage."
        ),
    )
