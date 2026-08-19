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


_GENERIC_CONTEXT = CapabilitySeoContextV1(
    product_name="Aspose.Words FOSS for Python",
    platform="Python",
    primary_input="",
    primary_output="",
)
_GENERIC_CAPABILITY = "Third-party plugin integration support"


def test_grounded_keyword_changes_the_generic_fallback_title_bytes() -> None:
    fallback = seo_capability_title(_GENERIC_CAPABILITY, _GENERIC_CONTEXT)
    assert fallback == "Work with Third-party plugin integration support"

    keyword_title = seo_capability_title(
        _GENERIC_CAPABILITY, _GENERIC_CONTEXT, seo_keyword="plugin integration guide"
    )

    assert keyword_title == "Plugin integration guide"
    assert keyword_title != fallback


def test_no_keyword_or_ungrounded_keyword_restores_byte_identical_fallback() -> None:
    fallback = seo_capability_title(_GENERIC_CAPABILITY, _GENERIC_CONTEXT)

    assert seo_capability_title(_GENERIC_CAPABILITY, _GENERIC_CONTEXT, seo_keyword=None) == fallback
    assert (
        seo_capability_title(
            _GENERIC_CAPABILITY, _GENERIC_CONTEXT, seo_keyword="totally unrelated phrase"
        )
        == fallback
    )


def test_ungrounded_keyword_has_zero_effect_even_on_a_fact_bounded_branch() -> None:
    context = CapabilitySeoContextV1(
        product_name="Aspose.Words FOSS for Python",
        platform="Python",
        primary_input="DOC files",
        primary_output="PDF files",
    )

    assert (
        seo_capability_title("PDF export", context, seo_keyword="unrelated marketing phrase")
        == "Export PDF files"
    )
