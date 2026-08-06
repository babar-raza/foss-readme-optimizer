"""Build exact partial source-claim resolutions for verified policy corrections."""

from __future__ import annotations

import hashlib

from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.document_plan import SourceClaimResolutionV1
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validate_correction_bytes(
    correction: SourceClaimPolicyCorrectionV1,
    source_bytes: bytes,
    candidate_bytes: bytes,
) -> None:
    if correction.source_byte_end > len(source_bytes):
        raise ValueError("source policy correction exceeds the immutable source bytes")
    if correction.candidate_byte_end > len(candidate_bytes):
        raise ValueError("source policy correction exceeds the candidate bytes")
    if (
        _sha256(source_bytes[correction.source_byte_start : correction.source_byte_end])
        != correction.source_content_sha256
    ):
        raise ValueError("source policy correction source hash does not match its exact span")
    candidate_content = candidate_bytes[
        correction.candidate_byte_start : correction.candidate_byte_end
    ]
    if _sha256(candidate_content) != correction.candidate_content_sha256:
        raise ValueError("source policy correction candidate hash does not match its exact span")
    if correction.disposition == "omit" and candidate_content:
        raise ValueError("omit policy correction cannot own a nonempty candidate replacement")
    if correction.disposition != "omit" and not candidate_content:
        raise ValueError("non-omit policy correction requires its exact candidate replacement")


def _claim_scoped_correction(
    claim: ReadmeMaterialClaimAssessmentV1,
    correction: SourceClaimPolicyCorrectionV1,
    source_bytes: bytes,
) -> SourceClaimPolicyCorrectionV1:
    correction_inside_claim = (
        claim.source_byte_start <= correction.source_byte_start
        and correction.source_byte_end <= claim.source_byte_end
    )
    if correction_inside_claim:
        return correction
    claim_inside_correction = (
        correction.source_byte_start <= claim.source_byte_start
        and claim.source_byte_end <= correction.source_byte_end
    )
    if not claim_inside_correction:
        raise ValueError("source policy correction partially overlaps a material claim")
    if correction.disposition != "omit":
        raise ValueError("cannot clip a nonempty policy replacement to a material claim")
    claim_content = source_bytes[claim.source_byte_start : claim.source_byte_end]
    claim_hash = _sha256(claim_content)
    if claim_hash != claim.content_sha256:
        raise ValueError("material claim hash does not match its immutable source span")
    return correction.model_copy(
        update={
            "correction_id": (
                f"{correction.correction_id}.claim-"
                f"{claim.source_byte_start}-{claim.source_byte_end}"
            ),
            "source_byte_start": claim.source_byte_start,
            "source_byte_end": claim.source_byte_end,
            "source_content_sha256": claim_hash,
        }
    )


def _spans_cover_claim(
    claim: ReadmeMaterialClaimAssessmentV1,
    corrections: list[SourceClaimPolicyCorrectionV1],
) -> bool:
    cursor = claim.source_byte_start
    for correction in sorted(
        corrections,
        key=lambda item: (item.source_byte_start, item.source_byte_end),
    ):
        if correction.source_byte_end <= cursor:
            continue
        if correction.source_byte_start > cursor:
            return False
        cursor = max(cursor, correction.source_byte_end)
    return cursor == claim.source_byte_end


def source_policy_resolution(
    claim: ReadmeMaterialClaimAssessmentV1,
    corrections: list[SourceClaimPolicyCorrectionV1],
    *,
    source_bytes: bytes,
    candidate_bytes: bytes,
) -> SourceClaimResolutionV1 | None:
    """Bind policy spans overlapping one material claim without claiming its other bytes."""

    if (
        claim.source_byte_end > len(source_bytes)
        or _sha256(source_bytes[claim.source_byte_start : claim.source_byte_end])
        != claim.content_sha256
    ):
        raise ValueError("material claim hash does not match its immutable source span")
    owned = []
    for correction in corrections:
        if not (
            claim.source_byte_start < correction.source_byte_end
            and correction.source_byte_start < claim.source_byte_end
        ):
            continue
        _validate_correction_bytes(correction, source_bytes, candidate_bytes)
        owned.append(_claim_scoped_correction(claim, correction, source_bytes))
    if not owned:
        return None
    ordered = sorted(owned, key=lambda item: (item.source_byte_start, item.source_byte_end))
    if any(
        left.source_byte_end > right.source_byte_start
        for left, right in zip(ordered, ordered[1:], strict=False)
    ):
        raise ValueError("source policy corrections overlap within one material claim")
    comment_correction = any(
        "readme.no_comments" in correction.configured_standard_ids for correction in ordered
    )
    if comment_correction and not _spans_cover_claim(claim, ordered):
        return None
    return SourceClaimResolutionV1(
        claim_id=claim.claim_id,
        source_byte_start=claim.source_byte_start,
        source_byte_end=claim.source_byte_end,
        content_sha256=claim.content_sha256,
        resolution="presentation_policy_correction",
        policy_corrections=ordered,
        evidence=[
            f"source-claim:{claim.claim_id}",
            f"source-content-sha256:{claim.content_sha256}",
            *(f"policy-correction:{correction.correction_id}" for correction in ordered),
        ],
        rationale=(
            "Apply exact visitor-policy corrections inside the claim while retaining all "
            "unaffected bytes under source-exact lineage."
        ),
    )
