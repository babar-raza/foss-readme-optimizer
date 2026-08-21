"""Tests for the fact-layer document-format vocabulary."""

from readme_agent.facts.format_vocabulary import (
    canonical_document_format,
    parse_format_support_claim,
)


def test_format_vocabulary_accepts_formats_and_repository_aliases():
    assert canonical_document_format("pptx") == "PPTX"
    assert canonical_document_format("ThreeMf") == "3MF"
    assert canonical_document_format("Type1") == "TYPE1"
    assert parse_format_support_claim("export support for Pdf via PdfWriter") == (
        "export",
        "PDF",
    )


def test_format_vocabulary_rejects_method_and_render_option_tokens():
    for token in ("insert", "visit", "gray", "bilevel", "PdfV0", "ImagePage"):
        assert canonical_document_format(token) is None
        assert parse_format_support_claim(f"export support for {token} via Writer") is None
