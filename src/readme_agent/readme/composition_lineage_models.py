"""Typed exact source placements and final-candidate lineage segments."""

from __future__ import annotations

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LineageOrigin = Literal["source_preserved", "generated", "corrected"]
LineageAuthority = Literal[
    "source_exact",
    "unbound",
    "additive",
    "authoritative_fact_correction",
    "presentation_policy_correction",
]
SourcePlacementBasis = Literal[
    "structural_exact_equivalence",
    "composer_inserted_exact",
    "operation_unchanged_exact",
    "no_op_whole_source",
]

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_TREATMENTS = {
    "preserve",
    "additive",
    "authoritative_fact_correction",
    "presentation_policy_correction",
}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExactSourcePlacementV1(_StrictModel):
    """One exact source span placed at an exact final-candidate byte range."""

    placement_id: str
    placement_basis: SourcePlacementBasis
    source_owner_id: str | None = None
    structural_role: str | None = None
    source_byte_start: int = Field(ge=0)
    source_byte_end: int = Field(gt=0)
    source_content_sha256: str
    final_byte_start: int = Field(ge=0)
    final_byte_end: int = Field(gt=0)
    final_content_sha256: str

    @field_validator("source_content_sha256", "final_content_sha256")
    @classmethod
    def _valid_hash(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("source-placement hash must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def _valid_ranges(self) -> ExactSourcePlacementV1:
        if self.source_byte_end <= self.source_byte_start:
            raise ValueError("source placement must bind a nonempty source span")
        if self.final_byte_end <= self.final_byte_start:
            raise ValueError("source placement must bind a nonempty final span")
        if (
            self.source_byte_end - self.source_byte_start
            != self.final_byte_end - self.final_byte_start
        ):
            raise ValueError("source placement byte ranges must have equal lengths")
        if self.source_content_sha256 != self.final_content_sha256:
            raise ValueError("source placement source and final hashes must match")
        if (
            self.placement_basis
            in {
                "structural_exact_equivalence",
                "composer_inserted_exact",
            }
            and self.source_owner_id is None
        ):
            raise ValueError("composer source placements require one explicit source owner")
        if self.placement_basis == "structural_exact_equivalence":
            if not self.structural_role:
                raise ValueError("structural exact equivalence requires a governed role")
            if (
                self.structural_role != "opening_material_claim"
                and not self.structural_role.startswith("h2:")
            ):
                raise ValueError("structural exact equivalence has an unknown governed role")
        elif self.structural_role is not None:
            raise ValueError("structural role is reserved for structural exact equivalence")
        return self


class LineageProvenanceV1(_StrictModel):
    """Exact candidate span with typed authority or operation-lineage scope."""

    provenance_id: str
    authority_scope: Literal["factual_or_configured", "lineage_only"] = "factual_or_configured"
    lineage_operation_id: str | None = None
    candidate_byte_start: int = Field(ge=0)
    candidate_byte_end: int = Field(gt=0)
    fact_ids: list[str] = Field(default_factory=list)
    configured_standard_ids: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _complete_binding(self) -> LineageProvenanceV1:
        if self.candidate_byte_end <= self.candidate_byte_start:
            raise ValueError("lineage provenance requires a nonempty candidate span")
        if not (self.fact_ids or self.configured_standard_ids):
            raise ValueError("lineage provenance requires facts or governed standards")
        if self.authority_scope == "lineage_only" and self.fact_ids:
            raise ValueError("lineage-only provenance cannot claim factual authority")
        if self.authority_scope == "lineage_only" and not self.lineage_operation_id:
            raise ValueError("lineage-only provenance requires an exact operation owner")
        if self.authority_scope != "lineage_only" and self.lineage_operation_id is not None:
            raise ValueError("operation ownership is reserved for lineage-only provenance")
        return self


class FinalByteLineageSegmentV1(_StrictModel):
    """One nonempty, exact UTF-8-aligned final-candidate segment."""

    segment_id: str
    final_byte_start: int = Field(ge=0)
    final_byte_end: int = Field(gt=0)
    content_text: str
    content_sha256: str
    origin: LineageOrigin
    source_byte_start: int | None = Field(default=None, ge=0)
    source_byte_end: int | None = Field(default=None, ge=0)
    source_content_sha256: str | None = None
    fact_ids: list[str] = Field(default_factory=list)
    configured_standard_ids: list[str] = Field(default_factory=list)
    provenance_ids: list[str] = Field(default_factory=list)
    operation_ids: list[str] = Field(default_factory=list)
    protected_content_treatments: list[str] = Field(default_factory=list)
    authority: LineageAuthority

    @field_validator("content_sha256", "source_content_sha256")
    @classmethod
    def _valid_hash(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("lineage hashes must be lowercase SHA-256 values")
        return value

    @field_validator("protected_content_treatments")
    @classmethod
    def _valid_treatments(cls, value: list[str]) -> list[str]:
        if any(item not in _TREATMENTS for item in value):
            raise ValueError("lineage segment contains an unknown content treatment")
        return value

    @model_validator(mode="after")
    def _complete_origin(self) -> FinalByteLineageSegmentV1:
        if self.final_byte_end <= self.final_byte_start:
            raise ValueError("lineage segments must be nonempty")
        if len(self.content_text.encode("utf-8")) != self.final_byte_end - self.final_byte_start:
            raise ValueError("lineage segment text does not match its final byte range")
        if _sha256(self.content_text) != self.content_sha256:
            raise ValueError("lineage segment content hash changed")
        source_fields = (self.source_byte_start, self.source_byte_end, self.source_content_sha256)
        if self.origin == "source_preserved":
            if any(value is None for value in source_fields) or self.authority != "source_exact":
                raise ValueError(
                    "source lineage requires exact source coordinates, hash, and authority"
                )
            if self.source_byte_end <= self.source_byte_start:  # type: ignore[operator]
                raise ValueError("source lineage must bind a nonempty source span")
            if self.fact_ids or self.configured_standard_ids or self.provenance_ids:
                raise ValueError("source-exact lineage cannot claim generated authority")
        else:
            if any(value is not None for value in source_fields):
                raise ValueError("generated lineage cannot claim source coordinates")
            if self.authority == "source_exact":
                raise ValueError("generated lineage requires an edit authority")
            if self.authority == "unbound" and (
                self.fact_ids or self.configured_standard_ids or self.provenance_ids
            ):
                raise ValueError("unbound lineage cannot claim candidate authority")
            if self.authority != "unbound" and not (self.fact_ids or self.configured_standard_ids):
                raise ValueError("generated lineage requires facts or a governed standard")
        return self


class ReadmeCompositionLedgerV1(_StrictModel):
    """Gap-free final-candidate lineage proven against actual document operations."""

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
            if any(
                binding.authority_scope != "lineage_only"
                and binding.candidate_byte_start < placement.final_byte_end
                and placement.final_byte_start < binding.candidate_byte_end
                for placement in self.source_placements
            ):
                raise ValueError("lineage provenance overlaps exact source placement")
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
                covering_placement = next(
                    (
                        item
                        for item in self.source_placements
                        if item.final_byte_start <= segment.final_byte_start
                        and segment.final_byte_end <= item.final_byte_end
                    ),
                    None,
                )
                if covering_placement is None:
                    raise ValueError("source-exact segment lacks a typed source placement")
                expected_source_start = covering_placement.source_byte_start + (
                    segment.final_byte_start - covering_placement.final_byte_start
                )
                if segment.source_byte_start != expected_source_start:
                    raise ValueError("source-exact segment changed its placement mapping")
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
