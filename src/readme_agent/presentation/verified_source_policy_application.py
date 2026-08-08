"""Apply exact source-policy edits while retaining byte-addressed lineage."""

from __future__ import annotations

import hashlib

from readme_agent.presentation.verified_preservation_segments import (
    CandidateEdit,
    apply_edit,
    rebase_provenance,
)
from readme_agent.presentation.verified_source_policy import VerifiedSourcePolicyEditV1
from readme_agent.readme.composition_lineage_models import ExactSourcePlacementV1
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1


def _fragment_placement(
    placement: ExactSourcePlacementV1,
    *,
    suffix: str,
    source_start: int,
    source_end: int,
    final_start: int,
    source_bytes: bytes,
) -> ExactSourcePlacementV1:
    content_hash = hashlib.sha256(source_bytes[source_start:source_end]).hexdigest()
    return placement.model_copy(
        update={
            "placement_id": f"{placement.placement_id}.{suffix}",
            "source_byte_start": source_start,
            "source_byte_end": source_end,
            "source_content_sha256": content_hash,
            "final_byte_start": final_start,
            "final_byte_end": final_start + source_end - source_start,
            "final_content_sha256": content_hash,
        }
    )


def apply_verified_source_policy(
    candidate: str,
    source_text: str,
    source_placements: list[ExactSourcePlacementV1],
    provenance: list[CandidateContentProvenanceV1],
    edits: list[VerifiedSourcePolicyEditV1],
) -> tuple[
    str,
    list[ExactSourcePlacementV1],
    list[CandidateContentProvenanceV1],
    list[SourceClaimPolicyCorrectionV1],
]:
    """Apply policy edits only where exact source bytes were actually preserved."""

    rendered = candidate
    placements = source_placements
    bindings = provenance
    corrections: list[SourceClaimPolicyCorrectionV1] = []
    source_bytes = source_text.encode("utf-8")
    for source_edit in sorted(edits, key=lambda item: item.source_byte_start, reverse=True):
        owners = [
            placement
            for placement in placements
            if placement.source_byte_start <= source_edit.source_byte_start
            and source_edit.source_byte_end <= placement.source_byte_end
        ]
        if not owners:
            continue
        if len(owners) != 1:
            raise ValueError("verified source-policy span has ambiguous exact source ownership")
        owner = owners[0]
        final_start = (
            owner.final_byte_start + source_edit.source_byte_start - owner.source_byte_start
        )
        final_end = owner.final_byte_start + source_edit.source_byte_end - owner.source_byte_start
        if (
            rendered.encode("utf-8")[final_start:final_end]
            != source_bytes[source_edit.source_byte_start : source_edit.source_byte_end]
        ):
            raise ValueError("verified source-policy span no longer matches exact source bytes")
        candidate_edit = CandidateEdit(final_start, final_end, source_edit.replacement)
        delta = len(source_edit.replacement.encode("utf-8")) - (final_end - final_start)
        corrections = [
            correction.model_copy(
                update={
                    "candidate_byte_start": correction.candidate_byte_start + delta,
                    "candidate_byte_end": correction.candidate_byte_end + delta,
                }
            )
            if final_end <= correction.candidate_byte_start
            else correction
            for correction in corrections
        ]
        rebased: list[ExactSourcePlacementV1] = []
        for placement in placements:
            if placement.placement_id == owner.placement_id:
                if owner.source_byte_start < source_edit.source_byte_start:
                    rebased.append(
                        _fragment_placement(
                            owner,
                            suffix=f"policy-prefix-{source_edit.source_byte_start}",
                            source_start=owner.source_byte_start,
                            source_end=source_edit.source_byte_start,
                            final_start=owner.final_byte_start,
                            source_bytes=source_bytes,
                        )
                    )
                if source_edit.source_byte_end < owner.source_byte_end:
                    rebased.append(
                        _fragment_placement(
                            owner,
                            suffix=f"policy-suffix-{source_edit.source_byte_end}",
                            source_start=source_edit.source_byte_end,
                            source_end=owner.source_byte_end,
                            final_start=final_start + len(source_edit.replacement.encode("utf-8")),
                            source_bytes=source_bytes,
                        )
                    )
            elif placement.final_byte_end <= final_start:
                rebased.append(placement)
            elif final_end <= placement.final_byte_start:
                rebased.append(
                    placement.model_copy(
                        update={
                            "final_byte_start": placement.final_byte_start + delta,
                            "final_byte_end": placement.final_byte_end + delta,
                        }
                    )
                )
            else:
                raise ValueError("verified source-policy edit crosses exact source owners")
        rendered = apply_edit(rendered, candidate_edit)
        bindings = rebase_provenance(bindings, candidate_edit, rendered)
        provenance_id = None
        if source_edit.replacement:
            provenance_id = (
                f"source.policy.{source_edit.source_byte_start}-{source_edit.source_byte_end}"
            )
            bindings.append(
                CandidateContentProvenanceV1(
                    provenance_id=provenance_id,
                    candidate_byte_start=final_start,
                    candidate_byte_end=final_start + len(source_edit.replacement.encode("utf-8")),
                    fact_ids=source_edit.fact_ids,
                    configured_standard_ids=source_edit.configured_standard_ids,
                    rationale=source_edit.rationale,
                )
            )
        placements = rebased
        replacement_bytes = source_edit.replacement.encode("utf-8")
        corrections.append(
            SourceClaimPolicyCorrectionV1(
                correction_id=(
                    f"source.policy.{source_edit.source_byte_start}-{source_edit.source_byte_end}"
                ),
                disposition=(
                    "omit"
                    if not replacement_bytes
                    else (
                        "replace"
                        if any(
                            standard
                            in {
                                "readme.enterprise_edition_terminology",
                                "readme.heading_title_case",
                                "readme.technical_abbreviation_case",
                            }
                            for standard in source_edit.configured_standard_ids
                        )
                        else "unwrap"
                    )
                ),
                source_byte_start=source_edit.source_byte_start,
                source_byte_end=source_edit.source_byte_end,
                source_content_sha256=hashlib.sha256(
                    source_bytes[source_edit.source_byte_start : source_edit.source_byte_end]
                ).hexdigest(),
                candidate_byte_start=final_start,
                candidate_byte_end=final_start + len(replacement_bytes),
                candidate_content_sha256=hashlib.sha256(replacement_bytes).hexdigest(),
                fact_ids=source_edit.fact_ids,
                configured_standard_ids=source_edit.configured_standard_ids,
                replacement_provenance_id=provenance_id,
                operation_id="readme.verified-template.compile",
            )
        )
    return (
        rendered,
        placements,
        bindings,
        sorted(corrections, key=lambda item: item.source_byte_start),
    )


def rebase_source_policy_corrections(
    corrections: list[SourceClaimPolicyCorrectionV1],
    edit: CandidateEdit,
) -> list[SourceClaimPolicyCorrectionV1]:
    """Rebase exact final correction coordinates through a non-overlapping candidate edit."""

    delta = len(edit.replacement.encode("utf-8")) - (edit.byte_end - edit.byte_start)
    rebased = []
    for correction in corrections:
        if correction.candidate_byte_end <= edit.byte_start:
            rebased.append(correction)
        elif edit.byte_end <= correction.candidate_byte_start:
            rebased.append(
                correction.model_copy(
                    update={
                        "candidate_byte_start": correction.candidate_byte_start + delta,
                        "candidate_byte_end": correction.candidate_byte_end + delta,
                    }
                )
            )
        else:
            raise ValueError("candidate edit overlaps an exact source-policy replacement")
    return rebased
