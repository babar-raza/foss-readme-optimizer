"""Validate the gap-free README composition ledger aggregate."""

from __future__ import annotations

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from readme_agent.readme.composition_lineage_models import (
    ExactSourcePlacementV1,
    FinalByteLineageSegmentV1,
    LineageProvenanceV1,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ReadmeCompositionLedgerV1(BaseModel):
    """Gap-free final-candidate lineage proven against actual document operations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    source_sha256: str
    source_bytes: int = Field(ge=0)
    candidate_sha256: str
    candidate_bytes: int = Field(ge=0)
    operation_reconstruction_sha256: str
    source_placements: list[ExactSourcePlacementV1]
    candidate_provenance: list[LineageProvenanceV1] = Field(default_factory=list)
    segments: list[FinalByteLineageSegmentV1]

    @field_validator("source_sha256", "candidate_sha256", "operation_reconstruction_sha256")
    @classmethod
    def _valid_hash(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("composition-ledger hashes must be lowercase SHA-256 values")
        return value

    @model_validator(mode="after")
    def _gap_free_internal_reconstruction(self) -> ReadmeCompositionLedgerV1:
        segment_ids = [item.segment_id for item in self.segments]
        placement_ids = [item.placement_id for item in self.source_placements]
        provenance_ids = [item.provenance_id for item in self.candidate_provenance]
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError("composition ledger contains duplicate segment IDs")
        if len(placement_ids) != len(set(placement_ids)):
            raise ValueError("composition ledger contains duplicate source-placement IDs")
        if len(provenance_ids) != len(set(provenance_ids)):
            raise ValueError("composition ledger contains duplicate lineage-provenance IDs")
        for binding in self.candidate_provenance:
            if binding.candidate_byte_end > self.candidate_bytes:
                raise ValueError("lineage provenance exceeds candidate boundaries")
            if binding.authority_scope == "lineage_only":
                continue
            overlaps = [
                placement
                for placement in self.source_placements
                if binding.candidate_byte_start < placement.final_byte_end
                and placement.final_byte_start < binding.candidate_byte_end
            ]
            if overlaps and (
                len(overlaps) != 1
                or overlaps[0].placement_basis
                not in {"structural_exact_equivalence", "relocated_exact_equivalence"}
                or binding.candidate_byte_start < overlaps[0].final_byte_start
                or overlaps[0].final_byte_end < binding.candidate_byte_end
                or not binding.fact_ids
            ):
                raise ValueError("lineage provenance has an unsupported exact-source overlap")
        placement_cursor = 0
        source_placement_cursor = 0
        for placement in sorted(self.source_placements, key=lambda item: item.final_byte_start):
            if (
                placement.source_byte_end > self.source_bytes
                or placement.final_byte_end > self.candidate_bytes
            ):
                raise ValueError("composition source placement exceeds ledger boundaries")
            if placement.final_byte_start < placement_cursor:
                raise ValueError("composition source placements overlap")
            placement_cursor = placement.final_byte_end
        for placement in sorted(self.source_placements, key=lambda item: item.source_byte_start):
            if placement.source_byte_start < source_placement_cursor:
                raise ValueError("composition source bytes are placed more than once")
            source_placement_cursor = placement.source_byte_end
        final_cursor = 0
        reconstructed = bytearray()
        for segment in self.segments:
            if segment.final_byte_start != final_cursor:
                raise ValueError("composition lineage has a gap or overlap")
            reconstructed.extend(segment.content_text.encode("utf-8"))
            if segment.origin == "source_preserved":
                self._validate_source_segment(segment)
            final_cursor = segment.final_byte_end
        if final_cursor != self.candidate_bytes:
            raise ValueError("composition lineage does not cover every candidate byte")
        if hashlib.sha256(reconstructed).hexdigest() != self.candidate_sha256:
            raise ValueError("composition lineage does not reconstruct the candidate hash")
        for placement in self.source_placements:
            placement_segments = [
                segment
                for segment in self.segments
                if segment.final_byte_start < placement.final_byte_end
                and placement.final_byte_start < segment.final_byte_end
            ]
            placement_cursor = placement.final_byte_start
            for segment in placement_segments:
                if (
                    segment.origin != "source_preserved"
                    or segment.final_byte_start != placement_cursor
                ):
                    raise ValueError("source placement covers non-source or discontinuous lineage")
                placement_cursor = segment.final_byte_end
            if placement_cursor != placement.final_byte_end:
                raise ValueError("source placement is not fully covered by source lineage")
        return self

    def _validate_source_segment(self, segment: FinalByteLineageSegmentV1) -> None:
        covering = next(
            (
                item
                for item in self.source_placements
                if item.final_byte_start <= segment.final_byte_start
                and segment.final_byte_end <= item.final_byte_end
            ),
            None,
        )
        if covering is None:
            raise ValueError("source-exact segment lacks a typed source placement")
        expected_source_start = covering.source_byte_start + (
            segment.final_byte_start - covering.final_byte_start
        )
        if segment.source_byte_start != expected_source_start:
            raise ValueError("source-exact segment changed its placement mapping")
        source_fact_bindings = [
            binding
            for binding in self.candidate_provenance
            if binding.authority_scope != "lineage_only"
            and binding.candidate_byte_start <= segment.final_byte_start
            and segment.final_byte_end <= binding.candidate_byte_end
        ]
        expected_fact_ids = sorted(
            {fact_id for binding in source_fact_bindings for fact_id in binding.fact_ids}
        )
        expected_standard_ids = sorted(
            {
                standard_id
                for binding in source_fact_bindings
                for standard_id in binding.configured_standard_ids
            }
        )
        expected_provenance_ids = sorted(binding.provenance_id for binding in source_fact_bindings)
        if (
            segment.fact_ids != expected_fact_ids
            or segment.configured_standard_ids != expected_standard_ids
            or segment.provenance_ids != expected_provenance_ids
        ):
            raise ValueError("source segment authority differs from exact candidate provenance")
        expected_authority = "source_exact_fact_bound" if expected_fact_ids else "source_exact"
        if segment.authority != expected_authority:
            raise ValueError("source segment authority classification changed")
