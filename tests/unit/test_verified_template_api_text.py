"""role_sentence() must never emit an adjacent duplicate word."""

from __future__ import annotations

from readme_agent.presentation.verified_template_api_text import role_sentence


def test_role_suffix_self_referential_type_name_does_not_double_the_noun() -> None:
    """aspose-font-foss/Aspose.Font-FOSS-for-Python's real `Font` class ends with its
    own role suffix ("Font"). Stripping the suffix leaves an empty subject, which
    falls back to the product family noun ("font") -- the same word the template
    already appends, producing "Represents a font font through the Aspose.Font
    API." on the real candidate."""

    sentence = role_sentence("Font", "aspose.font", "font")

    assert sentence == "Represents a font through the Aspose.Font API."
    assert "font font" not in sentence.casefold()


def test_dom_interface_with_doubled_family_prefix_does_not_repeat_the_abbreviation() -> None:
    """`HTMLHtmlElement` is the real, correct W3C DOM interface name for the
    `<html>` tag (matching the browser JS interface of the same name). It splits
    into "HTML" + "Html" + "Element", and both "Html" tokens canonicalize to
    "HTML", producing "Represents an HTML HTML Element ..." on the real
    candidate."""

    sentence = role_sentence("HTMLHtmlElement", "aspose.html.dom.html", "html")

    assert sentence == "Represents an HTML Element in the public HTML API for Aspose.HTML."
    assert "HTML HTML" not in sentence


def test_module_domain_already_ending_in_api_does_not_double_it() -> None:
    """A real .NET module label can itself end in the word "API" (a legitimate
    namespace segment, e.g. "Core API"). The generic fallback sentence
    unconditionally appends " API" after the domain, so without collapsing this
    reads "Represents ... in the public Core API API for ...". Measured on the
    real portfolio: 3481 of 6567 distinct (name, module, family) triples hit
    exactly this pattern -- the largest single class of malformed description
    text found in the 2026-08-26 fleet pass."""

    sentence = role_sentence("FileFormat", "Core API", "3d")

    assert sentence == "Represents a File Format in the public Core API for Aspose.3D."
    assert "API API" not in sentence


def test_identifier_with_a_genuinely_repeated_word_is_also_collapsed() -> None:
    """The duplication is not always template-introduced: a compound identifier
    can repeat a word at its own internal boundary, e.g. a test method name
    combining "...Line" and "Line..." halves. Real example from the portfolio:
    `TestDrawLine_LineCapRound`."""

    sentence = role_sentence("TestDrawLine_LineCapRound", "Core API", "pdf")

    assert (
        sentence == "Represents a Test Draw Line Cap Round in the public Core API for Aspose.PDF."
    )


def test_ordinary_type_names_are_not_altered() -> None:
    """Negative control: normal names with no repeated word must render unchanged."""

    assert (
        role_sentence("Workbook", "aspose.cells", "cells")
        == "Represents a Workbook in the public Aspose.Cells API."
    )
    assert (
        role_sentence("PdfSaveOptions", "aspose.pdf", "pdf")
        == "Configures PDF output through the Aspose.PDF API."
    )
