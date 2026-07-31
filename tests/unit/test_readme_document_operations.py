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

    def test_equal_boundary_core_sections_have_stable_semantic_order(self):
        source = b"# Product\n"
        boundary = len(source)
        operations = [
            _op("readme.license.add-section", boundary, boundary, "LICENSE\n", source),
            _op("readme.header.badges", boundary, boundary, "BADGES\n", source),
            _op(
                "readme.example.add-verified-minimal",
                boundary,
                boundary,
                "QUICK START\n",
                source,
            ),
            _op(
                "readme.overview-navigation-and-acquisition",
                boundary,
                boundary,
                "OVERVIEW\n",
                source,
            ),
            _op("readme.journey.key-capabilities", boundary, boundary, "CAPABILITIES\n", source),
            _op("readme.installation.add-verified", boundary, boundary, "INSTALLATION\n", source),
            _op(
                "readme.links.insert-product-relationship",
                boundary,
                boundary,
                "RELATIONSHIP\n",
                source,
            ),
            _op(
                "readme.limitations.complete-verified",
                boundary,
                boundary,
                "EXTRA CONSTRAINTS\n",
                source,
            ),
            _op("readme.limitations.add-verified", boundary, boundary, "LIMITATIONS\n", source),
        ]

        rendered = apply_document_operations(source, list(reversed(operations)))

        assert rendered == (
            source
            + b"BADGES\nOVERVIEW\nCAPABILITIES\nINSTALLATION\nQUICK START\n"
            + b"RELATIONSHIP\nEXTRA CONSTRAINTS\nLIMITATIONS\nLICENSE\n"
        )
