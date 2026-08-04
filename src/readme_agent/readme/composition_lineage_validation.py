"""Independently validate persisted README composition lineage against exact bytes."""

from __future__ import annotations

import hashlib

from readme_agent.readme.composition_lineage_models import (
    LineageProvenanceV1,
    ReadmeCompositionLedgerV1,
)
from readme_agent.readme.composition_operation_origins import (
    legacy_operation_provenance,
    operation_basis_errors,
    replay_operation_origins,
)
from readme_agent.readme.document_operations import apply_document_operations
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    ReadmeDocumentOperationV1,
)


def _sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def composition_ledger_errors(
    ledger: ReadmeCompositionLedgerV1,
    source_text: str,
    candidate: str,
    operations: list[ReadmeDocumentOperationV1],
    candidate_provenance: list[CandidateContentProvenanceV1],
) -> list[str]:
    """Return exact stale, coverage, reconstruction, and operation-lineage failures."""

    errors: list[str] = []
    source = source_text.encode("utf-8")
    candidate_bytes = candidate.encode("utf-8")
    if ledger.source_sha256 != _sha256(source) or ledger.source_bytes != len(source):
        errors.append("composition ledger source hash or size changed")
    if ledger.candidate_sha256 != _sha256(candidate_bytes) or ledger.candidate_bytes != len(
        candidate_bytes
    ):
        errors.append("composition ledger candidate hash or size changed")
    expected_provenance = [
        LineageProvenanceV1.model_validate(binding.model_dump(mode="python"))
        for binding in candidate_provenance
    ]
    if ledger.candidate_provenance != expected_provenance:
        errors.append("plan candidate provenance differs from composition ledger projection")
    for placement in ledger.source_placements:
        all_provenance: list[CandidateContentProvenanceV1 | LineageProvenanceV1] = [
            *candidate_provenance,
            *ledger.candidate_provenance,
        ]
        declared_source_length = placement.source_byte_end - placement.source_byte_start
        declared_final_length = placement.final_byte_end - placement.final_byte_start
        source_content = source[placement.source_byte_start : placement.source_byte_end]
        final_content = candidate_bytes[placement.final_byte_start : placement.final_byte_end]
        if (
            placement.source_byte_end > len(source)
            or placement.final_byte_end > len(candidate_bytes)
            or len(source_content) != declared_source_length
            or len(final_content) != declared_final_length
            or source_content != final_content
            or _sha256(source_content) != placement.source_content_sha256
            or _sha256(final_content) != placement.final_content_sha256
        ):
            errors.append(f"{placement.placement_id}: exact source placement changed")
        try:
            source_content.decode("utf-8")
            final_content.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"{placement.placement_id}: placement is not UTF-8 aligned")
        overlaps = [
            binding.provenance_id
            for binding in all_provenance
            if binding.authority_scope != "lineage_only"
            and binding.candidate_byte_start < placement.final_byte_end
            and placement.final_byte_start < binding.candidate_byte_end
        ]
        if overlaps:
            errors.append(f"{placement.placement_id}: source placement overlaps provenance")
    reconstructed_segments = bytearray()
    final_cursor = 0
    for segment in ledger.segments:
        if segment.final_byte_start != final_cursor:
            errors.append(f"{segment.segment_id}: lineage has a gap or overlap")
        content = segment.content_text.encode("utf-8")
        final = candidate_bytes[segment.final_byte_start : segment.final_byte_end]
        if final != content or _sha256(final) != segment.content_sha256:
            errors.append(f"{segment.segment_id}: final bytes or hash changed")
        if segment.origin == "source_preserved":
            assert segment.source_byte_start is not None
            assert segment.source_byte_end is not None
            assert segment.source_content_sha256 is not None
            source_content = source[segment.source_byte_start : segment.source_byte_end]
            if (
                source_content != content
                or _sha256(source_content) != segment.source_content_sha256
            ):
                errors.append(f"{segment.segment_id}: exact source lineage changed")
            covering = [
                placement
                for placement in ledger.source_placements
                if placement.final_byte_start <= segment.final_byte_start
                and segment.final_byte_end <= placement.final_byte_end
            ]
            if len(covering) != 1:
                errors.append(f"{segment.segment_id}: source lineage placement is not unique")
        elif segment.provenance_ids:
            known_provenance_ids = {
                binding.provenance_id for binding in ledger.candidate_provenance
            }
            if not set(segment.provenance_ids).issubset(known_provenance_ids):
                errors.append(f"{segment.segment_id}: lineage provenance binding changed")
        if segment.authority == "unbound":
            errors.append(
                f"{segment.segment_id}: substantive generated bytes lack exact candidate authority"
            )
        reconstructed_segments.extend(content)
        final_cursor = segment.final_byte_end
    if final_cursor != len(candidate_bytes):
        errors.append("composition segments do not cover the candidate boundary")
    if bytes(reconstructed_segments) != candidate_bytes:
        errors.append("composition segments do not reconstruct exact candidate bytes")
    for placement in ledger.source_placements:
        overlapping_segments = [
            segment
            for segment in ledger.segments
            if segment.final_byte_start < placement.final_byte_end
            and placement.final_byte_start < segment.final_byte_end
        ]
        cursor = placement.final_byte_start
        for segment in overlapping_segments:
            if segment.origin != "source_preserved" or segment.final_byte_start != cursor:
                errors.append(
                    f"{placement.placement_id}: placement covers non-source "
                    "or discontinuous lineage"
                )
                break
            cursor = segment.final_byte_end
        if cursor != placement.final_byte_end:
            errors.append(f"{placement.placement_id}: placement lacks complete source lineage")
    try:
        replay = replay_operation_origins(source, operations)
    except ValueError as error:
        errors.append(f"composition origin replay failed: {error}")
    else:
        lineage_only = [
            binding for binding in candidate_provenance if binding.authority_scope == "lineage_only"
        ]
        if lineage_only != legacy_operation_provenance(replay):
            errors.append("plan lineage-only provenance differs from exact operation-origin replay")
        errors.extend(
            operation_basis_errors(
                ledger.source_placements,
                replay,
                source,
                candidate_bytes,
                operations,
            )
        )
    try:
        operation_reconstruction = apply_document_operations(source, operations)
    except ValueError as error:
        errors.append(f"composition operation reconstruction failed: {error}")
    else:
        if operation_reconstruction != candidate_bytes:
            errors.append("composition ledger is not equivalent to document operations")
        if _sha256(operation_reconstruction) != ledger.operation_reconstruction_sha256:
            errors.append("composition operation reconstruction hash changed")
    return errors
