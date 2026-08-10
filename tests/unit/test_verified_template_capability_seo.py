"""Regression tests for fact-bounded capability SEO titles."""

from readme_agent.presentation.verified_template_capability_seo import (
    CapabilitySeoContextV1,
    seo_capability_title,
)


def test_explicit_format_capability_keeps_its_verified_direction_and_subject() -> None:
    context = CapabilitySeoContextV1(
        product_name="Aspose.Words FOSS for Python",
        platform="Python",
        primary_input="DOC files",
        primary_output="DOCX files",
    )

    title = seo_capability_title(
        "Read and write DOCX documents using Python standard-library components",
        context,
    )

    assert title == "Read and write DOCX documents using Python standard-library components"
    assert "Convert DOC files" not in title


def test_generic_export_capability_still_uses_verified_repository_context() -> None:
    context = CapabilitySeoContextV1(
        product_name="Aspose.Words FOSS for Python",
        platform="Python",
        primary_input="DOC files",
        primary_output="PDF files",
    )

    assert seo_capability_title("PDF export", context) == "Export PDF files"
