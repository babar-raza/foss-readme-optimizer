"""Build final-byte lineage from actual placements, provenance, and operations."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from readme_agent.readme.composition_lineage_models import (
    ExactSourcePlacementV1,
    FinalByteLineageSegmentV1,
    LineageAuthority,
    LineageOrigin,
    LineageProvenanceV1,
    ReadmeCompositionLedgerV1,
)
from readme_agent.readme.composition_operation_origins import (
    derive_unchanged_source_placements,
    legacy_operation_provenance,
    operation_basis_errors,
    replay_operation_origins,
)
from readme_agent.readme.composition_source_fact_binding import (
    exact_source_fact_binding_placement,
)
from readme_agent.readme.document_operations import apply_document_operations
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    ReadmeDocumentOperationV1,
)

_MECHANICAL_STANDARD = "readme.composition.mechanical-markdown-v1"
_GOVERNED_STRUCTURAL_LINES = {
    "## Navigation",
    "## At a Glance",
    "## Key Capabilities",
    "## Installation",
    "## Quick Start",
    "## Scope and Limitations",
    "## Development and Testing",
    "### Tests",
    "## License",
}


def _sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _authority(treatments: Iterable[str]) -> LineageAuthority:
    values = set(treatments)
    if "authoritative_fact_correction" in values:
        return "authoritative_fact_correction"
    if "presentation_policy_correction" in values:
        return "presentation_policy_correction"
    if "additive" in values:
        return "additive"
    return "presentation_policy_correction"


def _is_governed_mechanical_structure(text: str) -> bool:
    """Recognize only punctuation/whitespace and configured document-shell headings."""

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(character.isalnum() for character in stripped):
            if stripped not in _GOVERNED_STRUCTURAL_LINES:
                return False
    return True


def _validated_placements(
    source: bytes,
    candidate: bytes,
    placements: list[ExactSourcePlacementV1],
) -> list[ExactSourcePlacementV1]:
    ordered = sorted(placements, key=lambda item: (item.final_byte_start, item.final_byte_end))
    previous_end = 0
    ids: set[str] = set()
    structural_owners: set[str] = set()
    for placement in ordered:
        if placement.placement_id in ids:
            raise ValueError("source placements contain duplicate IDs")
        ids.add(placement.placement_id)
        if placement.placement_basis in {
            "structural_exact_equivalence",
            "relocated_exact_equivalence",
        }:
            assert placement.source_owner_id is not None
            if placement.source_owner_id in structural_owners:
                raise ValueError("structural source owner has multiple final placements")
            structural_owners.add(placement.source_owner_id)
        if placement.final_byte_start < previous_end:
            raise ValueError("source placements overlap in final candidate bytes")
        if placement.source_byte_end > len(source) or placement.final_byte_end > len(candidate):
            raise ValueError("source placement exceeds source or candidate boundaries")
        source_content = source[placement.source_byte_start : placement.source_byte_end]
        candidate_content = candidate[placement.final_byte_start : placement.final_byte_end]
        if (
            len(source_content) != placement.source_byte_end - placement.source_byte_start
            or len(candidate_content) != placement.final_byte_end - placement.final_byte_start
            or source_content != candidate_content
            or _sha256(source_content) != placement.source_content_sha256
            or _sha256(candidate_content) != placement.final_content_sha256
        ):
            raise ValueError(f"exact source placement changed: {placement.placement_id}")
        try:
            source_content.decode("utf-8")
            candidate_content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("source placement is not UTF-8 boundary aligned") from error
        previous_end = placement.final_byte_end
    previous_source_end = 0
    for placement in sorted(ordered, key=lambda item: item.source_byte_start):
        if placement.source_byte_start < previous_source_end:
            raise ValueError("source placement reuses source bytes")
        previous_source_end = placement.source_byte_end
    return ordered


def build_composition_ledger(
    source_text: str,
    candidate: str,
    operations: list[ReadmeDocumentOperationV1],
    provenance: list[CandidateContentProvenanceV1],
    source_placements: list[ExactSourcePlacementV1] | None = None,
) -> ReadmeCompositionLedgerV1:
    """Return exact final-byte lineage proven equivalent to actual document operations."""

    source = source_text.encode("utf-8")
    candidate_bytes = candidate.encode("utf-8")
    operation_reconstruction = apply_document_operations(source, operations)
    if operation_reconstruction != candidate_bytes:
        raise ValueError("document operations do not reconstruct the composition candidate")
    replay = replay_operation_origins(source, operations)
    if replay.rendered != candidate_bytes:
        raise ValueError("operation-origin replay does not reconstruct the composition candidate")
    if not operations and source == candidate_bytes:
        source_placements = (
            [
                ExactSourcePlacementV1(
                    placement_id="source.noop.0000",
                    placement_basis="no_op_whole_source",
                    source_byte_start=0,
                    source_byte_end=len(source),
                    source_content_sha256=_sha256(source),
                    final_byte_start=0,
                    final_byte_end=len(source),
                    final_content_sha256=_sha256(source),
                )
            ]
            if source
            else []
        )
    elif source_placements is None:
        source_placements = derive_unchanged_source_placements(
            source, candidate_bytes, replay.source_origins
        )
    placements = _validated_placements(source, candidate_bytes, source_placements)
    basis_errors = operation_basis_errors(placements, replay, source, candidate_bytes, operations)
    if basis_errors:
        raise ValueError("; ".join(basis_errors))
    lineage_only = [item for item in provenance if item.authority_scope == "lineage_only"]
    expected_lineage_only = legacy_operation_provenance(replay)
    if lineage_only != expected_lineage_only:
        raise ValueError("lineage-only provenance differs from exact operation-origin replay")
    for binding in provenance:
        exact_source_fact_binding_placement(binding, placements)

    boundaries = {0, len(candidate_bytes)}
    for placement in placements:
        boundaries.update((placement.final_byte_start, placement.final_byte_end))
    for binding in provenance:
        if binding.candidate_byte_end > len(candidate_bytes):
            raise ValueError(
                f"candidate provenance exceeds candidate bytes: {binding.provenance_id}"
            )
        boundaries.update((binding.candidate_byte_start, binding.candidate_byte_end))
    segments: list[FinalByteLineageSegmentV1] = []
    for start, end in zip(sorted(boundaries), sorted(boundaries)[1:], strict=False):
        if start == end:
            continue
        text = candidate_bytes[start:end].decode("utf-8")
        covering_placement = next(
            (
                item
                for item in placements
                if item.final_byte_start <= start and end <= item.final_byte_end
            ),
            None,
        )
        interval_provenance = [
            item
            for item in provenance
            if item.candidate_byte_start < end and start < item.candidate_byte_end
        ]
        authority_provenance = [
            item for item in interval_provenance if item.authority_scope != "lineage_only"
        ]
        operation_ids = sorted(
            {item for item in replay.operation_origins[start:end] if item is not None}
        )
        interval_treatments = sorted(
            {item for item in replay.treatment_origins[start:end] if item is not None}
        )
        if covering_placement is not None:
            source_start = covering_placement.source_byte_start + (
                start - covering_placement.final_byte_start
            )
            source_end = source_start + (end - start)
            origin: LineageOrigin = "source_preserved"
            fact_ids = sorted({fact for item in authority_provenance for fact in item.fact_ids})
            standard_ids = sorted(
                {
                    standard
                    for item in authority_provenance
                    for standard in item.configured_standard_ids
                }
            )
            provenance_ids = sorted(item.provenance_id for item in authority_provenance)
            authority: LineageAuthority = "source_exact_fact_bound" if fact_ids else "source_exact"
            source_hash: str | None = _sha256(source[source_start:source_end])
            operation_ids = []
            interval_treatments = []
        else:
            source_start = None
            source_end = None
            source_hash = None
            fact_ids = sorted({fact for item in authority_provenance for fact in item.fact_ids})
            standard_ids = sorted(
                {
                    standard
                    for item in authority_provenance
                    for standard in item.configured_standard_ids
                }
            )
            if not (fact_ids or standard_ids):
                if not _is_governed_mechanical_structure(text):
                    authority = "unbound"
                else:
                    standard_ids = [_MECHANICAL_STANDARD]
            provenance_ids = sorted(item.provenance_id for item in authority_provenance)
            if authority_provenance or standard_ids:
                authority = _authority(interval_treatments)
            origin = (
                "corrected"
                if authority
                in {
                    "authoritative_fact_correction",
                    "presentation_policy_correction",
                }
                else "generated"
            )
        segments.append(
            FinalByteLineageSegmentV1(
                segment_id=f"composition.segment.{len(segments):04d}",
                final_byte_start=start,
                final_byte_end=end,
                content_text=text,
                content_sha256=_sha256(text),
                origin=origin,
                source_byte_start=source_start,
                source_byte_end=source_end,
                source_content_sha256=source_hash,
                fact_ids=fact_ids,
                configured_standard_ids=standard_ids,
                provenance_ids=provenance_ids,
                operation_ids=operation_ids,
                protected_content_treatments=interval_treatments,
                authority=authority,
            )
        )
    return ReadmeCompositionLedgerV1(
        source_sha256=_sha256(source),
        source_bytes=len(source),
        candidate_sha256=_sha256(candidate_bytes),
        candidate_bytes=len(candidate_bytes),
        operation_reconstruction_sha256=_sha256(operation_reconstruction),
        source_placements=placements,
        candidate_provenance=[
            LineageProvenanceV1.model_validate(item.model_dump(mode="python"))
            for item in provenance
        ],
        segments=segments,
    )
