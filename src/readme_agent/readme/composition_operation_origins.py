"""Replay document operations while retaining exact byte-origin ownership."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from readme_agent.readme.composition_lineage_models import ExactSourcePlacementV1
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_operations import ordered_document_operations
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    ReadmeDocumentOperationV1,
)


@dataclass(frozen=True)
class OperationOriginReplay:
    rendered: bytes
    source_origins: list[int | None]
    operation_origins: list[str | None]
    treatment_origins: list[str | None]


def replay_operation_origins(
    source: bytes,
    operations: list[ReadmeDocumentOperationV1],
) -> OperationOriginReplay:
    """Apply operations while retaining causal source and operation ownership per byte."""

    rendered = source
    source_origins: list[int | None] = list(range(len(source)))
    operation_origins: list[str | None] = [None] * len(source)
    treatments: list[str | None] = [None] * len(source)
    for operation in ordered_document_operations(operations):
        start = operation.source_byte_start
        end = operation.source_byte_end
        current = rendered[start:end]
        if sha256_hex(current) != operation.expected_sha256:
            raise ValueError(f"source span changed for {operation.operation_id}")
        replacement = operation.replacement_text.encode("utf-8")
        if replacement == current:
            replacement_origins = source_origins[start:end]
            replacement_operations = operation_origins[start:end]
            replacement_treatments = treatments[start:end]
        else:
            replacement_origins = [None] * len(replacement)
            replacement_operations = [operation.operation_id] * len(replacement)
            replacement_treatments = [operation.protected_content_treatment] * len(replacement)
        rendered = rendered[:start] + replacement + rendered[end:]
        source_origins = source_origins[:start] + replacement_origins + source_origins[end:]
        operation_origins = (
            operation_origins[:start] + replacement_operations + operation_origins[end:]
        )
        treatments = treatments[:start] + replacement_treatments + treatments[end:]
    return OperationOriginReplay(rendered, source_origins, operation_origins, treatments)


def derive_unchanged_source_placements(
    source: bytes,
    candidate: bytes,
    origins: list[int | None],
) -> list[ExactSourcePlacementV1]:
    """Return maximal contiguous source placements proven by replayed origins."""

    placements: list[ExactSourcePlacementV1] = []
    final_start = 0
    while final_start < len(origins):
        source_start = origins[final_start]
        if source_start is None:
            final_start += 1
            continue
        final_end = final_start + 1
        while (
            final_end < len(origins)
            and origins[final_end] is not None
            and origins[final_end] == source_start + (final_end - final_start)
        ):
            final_end += 1
        source_end = source_start + (final_end - final_start)
        content = source[source_start:source_end]
        if content != candidate[final_start:final_end]:
            raise ValueError("replayed source placement does not match final candidate bytes")
        content_hash = hashlib.sha256(content).hexdigest()
        placements.append(
            ExactSourcePlacementV1(
                placement_id=f"operation.source-placement.{len(placements):04d}",
                placement_basis="operation_unchanged_exact",
                source_byte_start=source_start,
                source_byte_end=source_end,
                source_content_sha256=content_hash,
                final_byte_start=final_start,
                final_byte_end=final_end,
                final_content_sha256=content_hash,
            )
        )
        final_start = final_end
    return placements


def legacy_operation_provenance(
    replay: OperationOriginReplay,
) -> list[CandidateContentProvenanceV1]:
    """Bind each exact legacy replacement run to its governing document operation."""

    provenance: list[CandidateContentProvenanceV1] = []
    start = 0
    while start < len(replay.operation_origins):
        operation_id = replay.operation_origins[start]
        if operation_id is None:
            start += 1
            continue
        end = start + 1
        while end < len(replay.operation_origins) and replay.operation_origins[end] == operation_id:
            end += 1
        provenance.append(
            CandidateContentProvenanceV1(
                provenance_id=f"document-operation.{operation_id}.{len(provenance):04d}",
                authority_scope="lineage_only",
                lineage_operation_id=operation_id,
                candidate_byte_start=start,
                candidate_byte_end=end,
                configured_standard_ids=[f"readme.document-operation.{operation_id}"],
                rationale="Bind exact generated bytes to their governed document operation.",
            )
        )
        start = end
    return provenance


def operation_basis_errors(
    placements: list[ExactSourcePlacementV1],
    replay: OperationOriginReplay,
    source: bytes,
    candidate: bytes,
    operations: list[ReadmeDocumentOperationV1],
) -> list[str]:
    """Return placement-basis claims not proven by the actual ordered-operation replay."""

    errors: list[str] = []
    no_op = [item for item in placements if item.placement_basis == "no_op_whole_source"]
    if no_op and (
        operations
        or source != candidate
        or len(placements) != 1
        or no_op[0].source_byte_start != 0
        or no_op[0].source_byte_end != len(source)
        or no_op[0].final_byte_start != 0
        or no_op[0].final_byte_end != len(candidate)
    ):
        errors.append("no_op_whole_source is not the sole exact zero-operation placement")
    for placement in placements:
        if placement.placement_basis != "operation_unchanged_exact":
            continue
        final_origins = replay.source_origins[placement.final_byte_start : placement.final_byte_end]
        expected = list(range(placement.source_byte_start, placement.source_byte_end))
        if final_origins != expected:
            errors.append(
                f"{placement.placement_id}: operation_unchanged_exact lacks replayed origins"
            )
    return errors
