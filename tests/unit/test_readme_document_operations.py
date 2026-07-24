"""Focused tests for the extracted document-operation engine."""

import pytest

from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_operations import apply_document_operations, build_operation


def _op(operation_id, start, end, replacement, source, operation="replace"):
    return build_operation(
        operation_id=operation_id,
        operation=operation,
        source=source,
        start=start,
        end=end,
        replacement=replacement,
        fact_ids=[],
        treatment="additive",
        rationale="test",
    )


class TestBuildOperation:
    def test_stamps_span_and_replacement_hashes(self):
        source = b"hello world"
        op = _op("test.op", 0, 5, "HELLO", source)
        assert op.expected_sha256 == sha256_hex(b"hello")
        assert op.replacement_sha256 == sha256_hex(b"HELLO")

    def test_stamps_fixed_validator_rollback_and_stop_contract(self):
        op = _op("test.op", 0, 5, "HELLO", b"hello world")
        assert op.validators == [
            "source_span_hash",
            "fact_citations",
            "protected_content",
            "document_reconstruction",
            "independent_verifier",
        ]
        assert op.rollback.startswith("Restore the exact immutable source bytes")
        assert "immutable source revision changed" in op.stop_conditions


class TestApplyDocumentOperations:
    def test_single_replacement(self):
        source = b"hello world"
        op = _op("test.op", 0, 5, "HELLO", source)
        assert apply_document_operations(source, [op]) == b"HELLO world"

    def test_multiple_non_overlapping_apply_in_reverse_byte_order(self):
        source = b"hello world"
        op1 = _op("test.first", 0, 5, "HELLO", source)
        op2 = _op("test.second", 6, 11, "WORLD", source)
        assert apply_document_operations(source, [op1, op2]) == b"HELLO WORLD"

    def test_source_span_hash_mismatch_raises(self):
        source = b"hello world"
        op = _op("test.op", 0, 5, "HELLO", source)
        with pytest.raises(ValueError, match="source span changed for test.op"):
            apply_document_operations(b"XXXXX world", [op])

    def test_empty_operations_returns_source_unchanged(self):
        assert apply_document_operations(b"unchanged", []) == b"unchanged"
