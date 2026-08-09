"""Resolve exact source placements and disjoint generated provenance."""

from __future__ import annotations

import hashlib

from readme_agent.presentation.verified_preservation_sections import PreservedBlock
from readme_agent.presentation.verified_preservation_segments import CandidateEdit
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.composition_lineage_models import ExactSourcePlacementV1
from readme_agent.readme.composition_source_fact_binding import (
    exact_source_fact_binding_placement,
)
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.document_structure import heading_identity, parse_headings


def _block_separator(markdown: str) -> str:
    if markdown.endswith("\n\n"):
        return ""
    if markdown.endswith("\n"):
        return "\n"
    return "\n\n"


def separated_exact_blocks(blocks: list[PreservedBlock]) -> str:
    """Keep each source block exact while generating a structural boundary after it."""

    return "".join(block.markdown + _block_separator(block.markdown) for block in blocks)


def replacement_placements(
    blocks: list[PreservedBlock],
    edit: CandidateEdit,
    placement_prefix: str,
    *,
    leading: str = "",
    separated: bool = True,
) -> list[ExactSourcePlacementV1]:
    """Bind each exact source block to its byte range inside an insertion replacement."""

    cursor = len(leading.encode("utf-8"))
    placements: list[ExactSourcePlacementV1] = []
    for index, block in enumerate(blocks):
        content = block.markdown.encode("utf-8")
        content_hash = hashlib.sha256(content).hexdigest()
        placements.append(
            ExactSourcePlacementV1(
                placement_id=f"{placement_prefix}.{index:04d}",
                placement_basis="composer_inserted_exact",
                source_owner_id=block.source_owner_id,
                source_byte_start=block.source_byte_start,
                source_byte_end=block.source_byte_end,
                source_content_sha256=content_hash,
                final_byte_start=edit.byte_start + cursor,
                final_byte_end=edit.byte_start + cursor + len(content),
                final_content_sha256=content_hash,
            )
        )
        cursor += len(content)
        if separated:
            cursor += len(_block_separator(block.markdown))
    return placements


def resolve_preserve_claim_placements(
    candidate: str,
    source_text: str,
    assessment: ReadmeAssessmentV1,
    replaceable_claim_ids: set[str],
    fact_authorized_claim_ids: set[str],
    existing_placements: list[ExactSourcePlacementV1],
) -> tuple[list[PreservedBlock], list[ExactSourcePlacementV1]]:
    """Return missing preserve blocks and uniquely governed structural equivalences."""

    source = source_text.encode("utf-8")
    candidate_bytes = candidate.encode("utf-8")
    source_headings = [heading for heading in parse_headings(source_text) if heading.level == 2]
    candidate_headings = [heading for heading in parse_headings(candidate) if heading.level == 2]
    navigation_ranges = [
        (
            len(source_text[: heading.start].encode("utf-8")),
            len(source_text[: heading.section_end].encode("utf-8")),
        )
        for heading in source_headings
        if heading_identity(heading.title) == "navigation"
    ]

    def structural_candidate_range(
        source_start: int, source_end: int
    ) -> tuple[int, int, str] | None:
        source_heading = next(
            (
                heading
                for heading in source_headings
                if len(source_text[: heading.start].encode("utf-8")) <= source_start
                and source_end <= len(source_text[: heading.section_end].encode("utf-8"))
            ),
            None,
        )
        if source_heading is None:
            source_opening_end = min(
                (len(source_text[: heading.start].encode("utf-8")) for heading in source_headings),
                default=len(source),
            )
            if source_end > source_opening_end:
                return None
            candidate_opening_end = min(
                (len(candidate[: heading.start].encode("utf-8")) for heading in candidate_headings),
                default=len(candidate_bytes),
            )
            return 0, candidate_opening_end, "opening_material_claim"
        identity = heading_identity(source_heading.title)
        matches = [
            heading for heading in candidate_headings if heading_identity(heading.title) == identity
        ]
        if len(matches) != 1:
            return None
        return (
            len(candidate[: matches[0].start].encode("utf-8")),
            len(candidate[: matches[0].section_end].encode("utf-8")),
            f"h2:{identity}",
        )

    missing: list[PreservedBlock] = []
    adopted: list[ExactSourcePlacementV1] = []
    for claim in assessment.material_claims:
        is_navigation_claim = any(
            start <= claim.source_byte_start and claim.source_byte_end <= end
            for start, end in navigation_ranges
        )
        if (
            claim.disposition != "preserve"
            or claim.claim_id in replaceable_claim_ids
            or is_navigation_claim
        ):
            continue
        block = source[claim.source_byte_start : claim.source_byte_end]
        all_placements = [*existing_placements, *adopted]
        if any(
            placement.source_byte_start <= claim.source_byte_start
            and claim.source_byte_end <= placement.source_byte_end
            for placement in all_placements
        ):
            continue
        structural_range = structural_candidate_range(
            claim.source_byte_start, claim.source_byte_end
        )
        if structural_range is not None:
            region_start, region_end, structural_role = structural_range
            region = candidate_bytes[region_start:region_end]
            if region.count(block) == 1:
                final_start = region_start + region.index(block)
                final_end = final_start + len(block)
                if any(
                    placement.final_byte_start < final_end
                    and final_start < placement.final_byte_end
                    for placement in all_placements
                ):
                    raise ValueError(f"structural source placements overlap: {claim.claim_id}")
                block_hash = hashlib.sha256(block).hexdigest()
                adopted.append(
                    ExactSourcePlacementV1(
                        placement_id=f"source.structural-claim.{len(adopted):04d}",
                        placement_basis="structural_exact_equivalence",
                        source_owner_id=claim.claim_id,
                        structural_role=structural_role,
                        source_byte_start=claim.source_byte_start,
                        source_byte_end=claim.source_byte_end,
                        source_content_sha256=block_hash,
                        final_byte_start=final_start,
                        final_byte_end=final_end,
                        final_content_sha256=block_hash,
                    )
                )
                continue
        if candidate_bytes.count(block) == 1 and claim.claim_id in fact_authorized_claim_ids:
            final_start = candidate_bytes.index(block)
            final_end = final_start + len(block)
            target_headings = [
                heading
                for heading in candidate_headings
                if len(candidate[: heading.start].encode("utf-8")) <= final_start
                and final_end <= len(candidate[: heading.section_end].encode("utf-8"))
            ]
            if len(target_headings) == 1:
                if any(
                    placement.final_byte_start < final_end
                    and final_start < placement.final_byte_end
                    for placement in all_placements
                ):
                    raise ValueError(f"relocated source placements overlap: {claim.claim_id}")
                block_hash = hashlib.sha256(block).hexdigest()
                adopted.append(
                    ExactSourcePlacementV1(
                        placement_id=f"source.relocated-claim.{len(adopted):04d}",
                        placement_basis="relocated_exact_equivalence",
                        source_owner_id=claim.claim_id,
                        structural_role=f"h2:{heading_identity(target_headings[0].title)}",
                        source_byte_start=claim.source_byte_start,
                        source_byte_end=claim.source_byte_end,
                        source_content_sha256=block_hash,
                        final_byte_start=final_start,
                        final_byte_end=final_end,
                        final_content_sha256=block_hash,
                    )
                )
                continue
        if block in candidate_bytes:
            raise ValueError(
                "preserve claim collides with unowned identical candidate bytes; "
                f"explicit source placement required: {claim.claim_id}"
            )
        try:
            markdown = block.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("preserve claim does not align to UTF-8 source bytes") from error
        missing.append(
            PreservedBlock(
                markdown=markdown,
                source_owner_id=claim.claim_id,
                source_byte_start=claim.source_byte_start,
                source_byte_end=claim.source_byte_end,
            )
        )
    return missing, adopted


def exclude_source_placements_from_provenance(
    provenance: list[CandidateContentProvenanceV1],
    placements: list[ExactSourcePlacementV1],
) -> list[CandidateContentProvenanceV1]:
    """Separate source bytes from provenance, retaining only exact prior fact bindings."""

    rebased: list[CandidateContentProvenanceV1] = []
    for binding in provenance:
        overlaps = [
            placement
            for placement in placements
            if binding.candidate_byte_start < placement.final_byte_end
            and placement.final_byte_start < binding.candidate_byte_end
        ]
        structural = [
            placement
            for placement in overlaps
            if placement.placement_basis == "structural_exact_equivalence"
        ]
        if structural:
            retained = exact_source_fact_binding_placement(binding, structural)
            if retained is not None:
                rebased.append(binding)
                continue
        relocated = [
            placement
            for placement in overlaps
            if placement.placement_basis == "relocated_exact_equivalence"
        ]
        if relocated and (binding.authority_scope == "lineage_only" or not binding.fact_ids):
            raise ValueError(
                "source placement overlaps generated provenance with an unsupported "
                f"exact-source binding: {binding.provenance_id}"
            )
        boundaries = {binding.candidate_byte_start, binding.candidate_byte_end}
        for placement in overlaps:
            boundaries.add(max(binding.candidate_byte_start, placement.final_byte_start))
            boundaries.add(min(binding.candidate_byte_end, placement.final_byte_end))
        points = sorted(boundaries)
        intervals = list(zip(points[:-1], points[1:], strict=True))
        retained_intervals: list[tuple[int, int]] = []
        for start, end in intervals:
            owners = [
                placement
                for placement in overlaps
                if placement.final_byte_start <= start and end <= placement.final_byte_end
            ]
            if not owners:
                retained_intervals.append((start, end))
                continue
            if (
                len(owners) == 1
                and owners[0].placement_basis
                in {"structural_exact_equivalence", "relocated_exact_equivalence"}
                and binding.authority_scope != "lineage_only"
                and binding.fact_ids
            ):
                retained_intervals.append((start, end))
        for index, (start, end) in enumerate(retained_intervals):
            unchanged = (
                len(retained_intervals) == 1
                and start == binding.candidate_byte_start
                and end == binding.candidate_byte_end
            )
            rebased.append(
                binding.model_copy(
                    update={
                        "provenance_id": (
                            binding.provenance_id
                            if unchanged
                            else f"{binding.provenance_id}.lineage-part-{index:04d}"
                        ),
                        "candidate_byte_start": start,
                        "candidate_byte_end": end,
                    }
                )
            )
    return rebased
