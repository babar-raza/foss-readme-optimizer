"""Bounded byte-span document operations: construction and hash-checked application.

``build_operation`` stamps each edit with the fixed validator/rollback/stop-condition
contract and the source/replacement span hashes; ``apply_document_operations`` applies
a set of non-overlapping operations in reverse byte order, re-verifying each source span
hash before it edits. Extracted verbatim from the former single-file ``document_renderer``
(`GOVERNANCE.md` "no monoliths").
"""

from __future__ import annotations

from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_plan import (
    DocumentOperation,
    ProtectedContentTreatment,
    ReadmeDocumentOperationV1,
)


def build_operation(
    *,
    operation_id: str,
    operation: DocumentOperation,
    source: bytes,
    start: int,
    end: int,
    replacement: str,
    fact_ids: list[str],
    treatment: ProtectedContentTreatment,
    rationale: str,
) -> ReadmeDocumentOperationV1:
    replacement_bytes = replacement.encode("utf-8")
    return ReadmeDocumentOperationV1(
        operation_id=operation_id,
        operation=operation,
        source_byte_start=start,
        source_byte_end=end,
        expected_sha256=sha256_hex(source[start:end]),
        replacement_text=replacement,
        replacement_sha256=sha256_hex(replacement_bytes),
        fact_ids=fact_ids,
        protected_content_treatment=treatment,
        rationale=rationale,
        validators=[
            "source_span_hash",
            "fact_citations",
            "protected_content",
            "document_reconstruction",
            "independent_verifier",
        ],
        rollback="Restore the exact immutable source bytes for this operation.",
        stop_conditions=[
            "immutable source revision changed",
            "source span checksum changed",
            "a cited fact is no longer selected and accepted",
            "protected content outside an authoritative correction would be lost",
        ],
    )


def apply_document_operations(source: bytes, operations: list[ReadmeDocumentOperationV1]) -> bytes:
    rendered = source
    for operation in sorted(
        operations,
        key=lambda item: (item.source_byte_start, item.source_byte_end),
        reverse=True,
    ):
        current = rendered[operation.source_byte_start : operation.source_byte_end]
        if sha256_hex(current) != operation.expected_sha256:
            raise ValueError(f"source span changed for {operation.operation_id}")
        rendered = (
            rendered[: operation.source_byte_start]
            + operation.replacement_text.encode("utf-8")
            + rendered[operation.source_byte_end :]
        )
    return rendered


def prune_noop_operations(
    source: bytes,
    operations: list[ReadmeDocumentOperationV1],
) -> list[ReadmeDocumentOperationV1]:
    """Discard operations whose replacement is already the exact immutable source span."""

    return [
        operation
        for operation in operations
        if source[operation.source_byte_start : operation.source_byte_end]
        != operation.replacement_text.encode("utf-8")
    ]
