"""Validate complete claim maps against immutable documents and operations."""

from __future__ import annotations

import hashlib

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.claim_accountability_models import (
    ClaimAccountabilityValidationV1,
    ReadmeClaimAccountabilityMapV1,
)
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1


def _sha256(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _operation_overlaps(
    operation: ReadmeDocumentOperationV1,
    start: int,
    end: int,
) -> bool:
    if operation.source_byte_start == operation.source_byte_end:
        return start <= operation.source_byte_start <= end
    return operation.source_byte_start < end and start < operation.source_byte_end


def validate_claim_accountability_map(
    accountability: ReadmeClaimAccountabilityMapV1,
    *,
    source_text: str,
    candidate_text: str,
    facts: ProductFactsV2,
    operations: list[ReadmeDocumentOperationV1],
) -> ClaimAccountabilityValidationV1:
    """Fail closed on missing units, stale spans, or correction-without-operation."""

    source_records = [record for record in accountability.claims if record.stage == "source"]
    candidate_records = [record for record in accountability.claims if record.stage == "candidate"]
    source_bytes = source_text.encode("utf-8")
    candidate_bytes = candidate_text.encode("utf-8")
    checks = {
        "repository_matches": accountability.org_repo == facts.org_repo,
        "facts_hash_matches": accountability.facts_hash == facts.canonical_hash(),
        "source_hash_matches": accountability.source_sha256 == _sha256(source_bytes),
        "candidate_hash_matches": accountability.candidate_sha256 == _sha256(candidate_bytes),
        "source_inventory_complete": len(source_records)
        == len(assess_material_claims(source_text)),
        "candidate_inventory_complete": len(candidate_records)
        == len(assess_material_claims(candidate_text)),
        "claim_ids_unique": len({record.claim_id for record in accountability.claims})
        == len(accountability.claims),
    }
    exact_spans = True
    for record in accountability.claims:
        document = source_bytes if record.stage == "source" else candidate_bytes
        content = document[record.source_byte_start : record.source_byte_end]
        if _sha256(content) != record.content_sha256:
            exact_spans = False
            break
    checks["claim_spans_exact"] = exact_spans

    correction_operations = all(
        record.survives_in_candidate is False
        and any(
            _operation_overlaps(
                operation,
                record.source_byte_start,
                record.source_byte_end,
            )
            for operation in operations
        )
        for record in source_records
        if record.expected_disposition == "required_correction"
    )
    checks["corrections_have_operations"] = correction_operations
    errors = [f"{name} failed" for name, passed in checks.items() if not passed]
    blocking = sorted(
        record.claim_id for record in accountability.claims if not record.currently_accountable
    )
    valid = not errors
    return ClaimAccountabilityValidationV1(
        valid=valid,
        approval_eligible=valid and not blocking,
        checks=checks,
        errors=errors,
        blocking_claim_ids=blocking,
    )
