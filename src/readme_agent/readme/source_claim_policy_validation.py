"""Validate exact policy-correction spans and retained source-claim lineage."""

from __future__ import annotations

import hashlib

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_accountability_models import ReadmeClaimAccountabilityV1
from readme_agent.readme.composition_lineage_models import ReadmeCompositionLedgerV1
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    ReadmeDocumentOperationV1,
    SourceClaimResolutionV1,
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _selected_accepted_facts(fact_ids: list[str], facts: ProductFactsV2) -> bool:
    for fact_id in fact_ids:
        try:
            fact = facts.fact_by_id(fact_id)
        except KeyError:
            return False
        if (
            facts.selected_fact_ids.get(fact.field) != fact_id
            or fact.verification_state not in {"verified", "policy_approved"}
            or fact.has_unresolved_conflict
        ):
            return False
    return True


def _operation_overlaps(operation: ReadmeDocumentOperationV1, start: int, end: int) -> bool:
    return (
        operation.coordinate_space == "presentation_inner_utf8"
        and operation.source_byte_start < end
        and start < operation.source_byte_end
    )


def policy_corrections_have_exact_partial_lineage(
    resolutions: dict[str, SourceClaimResolutionV1],
    source_records: dict[str, ReadmeClaimAccountabilityV1],
    source_bytes: bytes,
    candidate_bytes: bytes,
    facts: ProductFactsV2,
    operations: list[ReadmeDocumentOperationV1],
    provenance: list[CandidateContentProvenanceV1],
    composition_ledger: ReadmeCompositionLedgerV1 | None,
) -> bool:
    """Require correction spans plus exact placements to cover every original claim byte."""

    provenance_by_id = {binding.provenance_id: binding for binding in provenance}
    operation_by_id = {operation.operation_id: operation for operation in operations}
    placements = [] if composition_ledger is None else composition_ledger.source_placements
    for resolution in resolutions.values():
        if resolution.resolution != "presentation_policy_correction":
            continue
        record = source_records.get(resolution.claim_id)
        if (
            record is None
            or record.survives_in_candidate is not False
            or record.expected_disposition != "presentation_policy_correction"
        ):
            return False
        covered = [
            (placement.source_byte_start, placement.source_byte_end)
            for placement in placements
            if placement.source_byte_start < resolution.source_byte_end
            and resolution.source_byte_start < placement.source_byte_end
        ]
        for correction in resolution.policy_corrections:
            source_content = source_bytes[correction.source_byte_start : correction.source_byte_end]
            candidate_content = candidate_bytes[
                correction.candidate_byte_start : correction.candidate_byte_end
            ]
            binding = (
                provenance_by_id.get(correction.replacement_provenance_id)
                if correction.replacement_provenance_id is not None
                else None
            )
            replacement_valid = (
                binding is None
                if correction.candidate_byte_start == correction.candidate_byte_end
                else binding is not None
                and binding.candidate_byte_start == correction.candidate_byte_start
                and binding.candidate_byte_end == correction.candidate_byte_end
                and binding.fact_ids == correction.fact_ids
                and binding.configured_standard_ids == correction.configured_standard_ids
            )
            operation = operation_by_id.get(correction.operation_id)
            if not (
                resolution.source_byte_start <= correction.source_byte_start
                and correction.source_byte_end <= resolution.source_byte_end
                and _sha256(source_content) == correction.source_content_sha256
                and _sha256(candidate_content) == correction.candidate_content_sha256
                and _selected_accepted_facts(correction.fact_ids, facts)
                and replacement_valid
                and operation is not None
                and _operation_overlaps(
                    operation,
                    correction.source_byte_start,
                    correction.source_byte_end,
                )
            ):
                return False
            covered.append((correction.source_byte_start, correction.source_byte_end))
        cursor = resolution.source_byte_start
        for start, end in sorted(covered):
            start = max(start, resolution.source_byte_start)
            end = min(end, resolution.source_byte_end)
            if end <= cursor:
                continue
            if start > cursor:
                return False
            cursor = max(cursor, end)
        if cursor != resolution.source_byte_end:
            return False
    return True
