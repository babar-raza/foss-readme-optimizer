"""Apply template density disclosures after exact source preservation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from readme_agent.presentation.template_compiler import select_density_profile
from readme_agent.presentation.template_schema import (
    TemplateSlot,
    load_repository_presentation_template,
)
from readme_agent.presentation.verified_preservation_segments import CandidateEdit, apply_edit
from readme_agent.presentation.verified_source_policy_application import (
    rebase_source_policy_corrections,
)
from readme_agent.readme.composition_lineage_models import ExactSourcePlacementV1
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.document_structure import heading_identity, parse_headings
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1

_DENSITY_SLOTS: tuple[TemplateSlot, ...] = (
    "additional_examples",
    "api_reference",
)
_DETAILS = re.compile(r"(?i)<details(?:\s|>)")
_DENSITY_STANDARD = "readme.secondary_detail_density"


@dataclass(frozen=True)
class VerifiedSourceDensity:
    candidate: str
    provenance: list[CandidateContentProvenanceV1]
    source_placements: list[ExactSourcePlacementV1]
    source_policy_corrections: list[SourceClaimPolicyCorrectionV1]


@dataclass(frozen=True)
class _DensityInsertion:
    byte_offset: int
    replacement: str
    provenance_id: str


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _source_fragment(
    placement: ExactSourcePlacementV1,
    *,
    fragment: str,
    source_start: int,
    source_end: int,
    final_start: int,
    source_bytes: bytes,
) -> ExactSourcePlacementV1:
    content_hash = _sha256(source_bytes[source_start:source_end])
    return placement.model_copy(
        update={
            "placement_id": f"{placement.placement_id}.density-{fragment}",
            "source_byte_start": source_start,
            "source_byte_end": source_end,
            "source_content_sha256": content_hash,
            "final_byte_start": final_start,
            "final_byte_end": final_start + source_end - source_start,
            "final_content_sha256": content_hash,
        }
    )


def _validate_source_placements(
    candidate: str,
    source_text: str,
    placements: list[ExactSourcePlacementV1],
) -> None:
    candidate_bytes = candidate.encode("utf-8")
    source_bytes = source_text.encode("utf-8")
    for placement in placements:
        source = source_bytes[placement.source_byte_start : placement.source_byte_end]
        rendered = candidate_bytes[placement.final_byte_start : placement.final_byte_end]
        if (
            source != rendered
            or _sha256(source) != placement.source_content_sha256
            or _sha256(rendered) != placement.final_content_sha256
        ):
            raise ValueError(
                f"density input has a stale exact source placement: {placement.placement_id}"
            )


def _rebase_source_placements(
    placements: list[ExactSourcePlacementV1],
    insertion: _DensityInsertion,
    source_bytes: bytes,
) -> list[ExactSourcePlacementV1]:
    offset = insertion.byte_offset
    delta = len(insertion.replacement.encode("utf-8"))
    rebased: list[ExactSourcePlacementV1] = []
    for placement in placements:
        if placement.final_byte_end <= offset:
            rebased.append(placement)
            continue
        if offset <= placement.final_byte_start:
            rebased.append(
                placement.model_copy(
                    update={
                        "final_byte_start": placement.final_byte_start + delta,
                        "final_byte_end": placement.final_byte_end + delta,
                    }
                )
            )
            continue
        source_split = placement.source_byte_start + offset - placement.final_byte_start
        rebased.extend(
            [
                _source_fragment(
                    placement,
                    fragment=f"prefix-{offset}",
                    source_start=placement.source_byte_start,
                    source_end=source_split,
                    final_start=placement.final_byte_start,
                    source_bytes=source_bytes,
                ),
                _source_fragment(
                    placement,
                    fragment=f"suffix-{offset}",
                    source_start=source_split,
                    source_end=placement.source_byte_end,
                    final_start=offset + delta,
                    source_bytes=source_bytes,
                ),
            ]
        )
    return sorted(rebased, key=lambda item: (item.final_byte_start, item.placement_id))


def _rebase_provenance(
    provenance: list[CandidateContentProvenanceV1],
    insertion: _DensityInsertion,
) -> list[CandidateContentProvenanceV1]:
    offset = insertion.byte_offset
    delta = len(insertion.replacement.encode("utf-8"))
    rebased: list[CandidateContentProvenanceV1] = []
    for binding in provenance:
        if binding.candidate_byte_end <= offset:
            rebased.append(binding)
        elif offset <= binding.candidate_byte_start:
            rebased.append(
                binding.model_copy(
                    update={
                        "candidate_byte_start": binding.candidate_byte_start + delta,
                        "candidate_byte_end": binding.candidate_byte_end + delta,
                    }
                )
            )
        else:
            rebased.extend(
                [
                    binding.model_copy(
                        update={
                            "provenance_id": f"{binding.provenance_id}.density-prefix-{offset}",
                            "candidate_byte_end": offset,
                        }
                    ),
                    binding.model_copy(
                        update={
                            "provenance_id": f"{binding.provenance_id}.density-suffix-{offset}",
                            "candidate_byte_start": offset + delta,
                            "candidate_byte_end": binding.candidate_byte_end + delta,
                        }
                    ),
                ]
            )
    rebased.append(
        CandidateContentProvenanceV1(
            provenance_id=insertion.provenance_id,
            candidate_byte_start=offset,
            candidate_byte_end=offset + delta,
            configured_standard_ids=[_DENSITY_STANDARD],
            rationale=(
                "Apply the selected presentation density profile without changing preserved "
                "repository bytes."
            ),
        )
    )
    return sorted(rebased, key=lambda item: (item.candidate_byte_start, item.provenance_id))


def _source_owned(
    start: int,
    end: int,
    placements: list[ExactSourcePlacementV1],
) -> bool:
    return any(
        placement.final_byte_start < end and start < placement.final_byte_end
        for placement in placements
    )


def apply_verified_source_density(
    candidate: str,
    source_text: str,
    provenance: list[CandidateContentProvenanceV1],
    source_placements: list[ExactSourcePlacementV1],
    source_policy_corrections: list[SourceClaimPolicyCorrectionV1],
) -> VerifiedSourceDensity:
    """Collapse only long, source-owned secondary slots selected by the template profile."""

    _validate_source_placements(candidate, source_text, source_placements)
    contract = load_repository_presentation_template()
    profile = select_density_profile(
        max(len(source_text.splitlines()), len(candidate.splitlines())),
        template=contract,
    )
    collapsed_slots = set(contract.profiles[profile].collapse_slots) & set(_DENSITY_SLOTS)
    slots_by_heading = {heading_identity(contract.headings[slot]): slot for slot in _DENSITY_SLOTS}
    candidate_bytes = candidate.encode("utf-8")
    insertions: list[_DensityInsertion] = []
    for heading in parse_headings(candidate):
        if heading.level != 2:
            continue
        slot = slots_by_heading.get(heading_identity(heading.title))
        body = candidate[heading.heading_end : heading.section_end]
        body_start = len(candidate[: heading.heading_end].encode("utf-8"))
        body_end = len(candidate[: heading.section_end].encode("utf-8"))
        if (
            slot not in collapsed_slots
            or sum(bool(line.strip()) for line in body.splitlines()) < 12
            or _DETAILS.search(body) is not None
            or not _source_owned(body_start, body_end, source_placements)
        ):
            continue
        label = contract.headings[slot].casefold()
        close_prefix = "" if candidate_bytes[:body_end].endswith(b"\n") else "\n"
        identity = f"{slot}.{body_start}"
        insertions.extend(
            [
                _DensityInsertion(
                    byte_offset=body_start,
                    replacement=f"\n<details>\n<summary>Show {label}</summary>\n",
                    provenance_id=f"source.density.{identity}.open",
                ),
                _DensityInsertion(
                    byte_offset=body_end,
                    replacement=f"{close_prefix}</details>\n\n",
                    provenance_id=f"source.density.{identity}.close",
                ),
            ]
        )

    rendered = candidate
    placements = source_placements
    bindings = provenance
    corrections = source_policy_corrections
    source_bytes = source_text.encode("utf-8")
    for insertion in sorted(insertions, key=lambda item: item.byte_offset, reverse=True):
        edit = CandidateEdit(insertion.byte_offset, insertion.byte_offset, insertion.replacement)
        placements = _rebase_source_placements(placements, insertion, source_bytes)
        bindings = _rebase_provenance(bindings, insertion)
        corrections = rebase_source_policy_corrections(corrections, edit)
        rendered = apply_edit(rendered, edit)

    _validate_source_placements(rendered, source_text, placements)
    return VerifiedSourceDensity(
        candidate=rendered,
        provenance=bindings,
        source_placements=placements,
        source_policy_corrections=corrections,
    )
