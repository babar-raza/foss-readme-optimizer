"""Regression tests for fact-bounded capability SEO titles."""

from readme_agent.presentation.verified_template_capability_seo import (
    CapabilitySeoContextV1,
    seo_capability_title,
)
from readme_agent.readme.capability_semantics import is_action_led_capability_title


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
        _GENERIC_CAPABILITY, _GENERIC_CONTEXT, seo_keyword="manage plugin integrations"
    )

    assert keyword_title == "Manage plugin integrations"
    assert keyword_title != fallback


def test_grounded_but_non_action_led_keyword_falls_back_instead_of_breaking_the_contract() -> None:
    """PWD-008, live on aspose-pdf-foss/Aspose-PDF-FOSS-for-Go, `consecutive_count: 6`:
    real `aspose.relevant_seo_keywords` values are search phrases like "open source PDF
    generation for Go developers" -- vocabulary-grounded against a real capability, but not
    themselves action-led. Compiled-presentation validation hard-rejects the whole
    candidate if any Key Capabilities title doesn't start with an approved verb, and this
    function's own docstring promises "an action-led, fact-bounded search phrase" for
    every return value -- a grounded keyword substitution must never break that guarantee
    just because it shares vocabulary with the row's capability."""

    context = CapabilitySeoContextV1(
        product_name="Aspose.PDF FOSS for Go",
        platform="Go",
        primary_input="",
        primary_output="",
    )

    title = seo_capability_title(
        "PDF generation for Go developers",
        context,
        seo_keyword="open source PDF generation for Go developers",
    )

    assert title == "Work with PDF generation for Go developers"
    assert is_action_led_capability_title(title)


def test_pre_fix_non_action_led_keyword_reproduces_the_live_failure(monkeypatch) -> None:
    """Negative control: without the action-led guard on the keyword branch specifically,
    the exact real keyword shape from aspose-pdf-foss/Go is returned verbatim (title-cased),
    which is what compiled-presentation validation was rejecting live. Only the guard's own
    check on the substituted `keyword_title` is disabled here -- the function's earlier,
    unrelated use of the same predicate on `title` is left real, so this isolates exactly
    the removed guard rather than short-circuiting the function through a different branch."""

    import readme_agent.presentation.verified_template_capability_seo as module

    real_is_action_led = module.is_action_led_capability_title
    keyword_title = "Open source PDF generation for Go developers"

    def patched(value: str) -> bool:
        if value == keyword_title:
            return True
        return real_is_action_led(value)

    monkeypatch.setattr(module, "is_action_led_capability_title", patched)

    context = CapabilitySeoContextV1(
        product_name="Aspose.PDF FOSS for Go",
        platform="Go",
        primary_input="",
        primary_output="",
    )

    title = module.seo_capability_title(
        "PDF generation for Go developers",
        context,
        seo_keyword="open source PDF generation for Go developers",
    )

    assert title == keyword_title


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
