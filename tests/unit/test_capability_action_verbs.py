"""Prove the action-led capability rule accepts real verbs and still rejects labels."""

from __future__ import annotations

import pytest

from readme_agent.readme.capability_semantics import (
    capability_action_verb,
    is_action_led_capability_title,
)


@pytest.mark.parametrize(
    "title",
    [
        # PF05 typescript canary: rejected before the vocabulary was widened,
        # costing five provider calls over three section-authoring attempts.
        "Triangulate polygonal geometry",
        "Tessellate curved surfaces",
        "Subdivide mesh faces",
        "Extrude 2D profiles",
        "Deform skinned meshes",
        "Scale scene units",
        "Translate node positions",
    ],
)
def test_geometry_titles_are_action_led(title: str) -> None:
    assert is_action_led_capability_title(title)


@pytest.mark.parametrize(
    "title",
    [
        "Read and write cell values",
        "Convert 3D scenes",
        "Apply cell styles",
        "Export mesh data",
        "Merge cell ranges and apply number formats",
        "Manage hyperlinks and defined names",
        "Configure page setup and print settings",
    ],
)
def test_previously_accepted_titles_still_pass(title: str) -> None:
    """Widening the vocabulary must never regress an already-accepted title."""

    assert is_action_led_capability_title(title)


@pytest.mark.parametrize(
    "title",
    [
        # Bare labels and noun phrases: the rule exists to reject these, and a
        # wider verb list must not let them through.
        "Configuration",
        "Lifecycle management",
        "Support",
        "Operations",
        "Validation",
        "Cell values and formulas",
        "Document properties",
        "Mesh geometry",
        "Workbook metadata",
    ],
)
def test_non_action_titles_are_still_rejected(title: str) -> None:
    assert not is_action_led_capability_title(title)


def test_action_verb_is_reported_for_a_matched_title() -> None:
    assert capability_action_verb("Triangulate polygonal geometry") is not None
    assert capability_action_verb("Mesh geometry") is None


@pytest.mark.parametrize(
    "title",
    [
        # PWD-008, live on aspose-pdf-foss/Aspose-PDF-FOSS-for-Go (`consecutive_count: 6`):
        # real `aspose.relevant_seo_keywords`/`aspose.seo_keywords` values, every one
        # leading with "open source" as this FOSS domain's most common noun phrase, not
        # the verb "open". The bare `open` accept-list entry matched the string prefix
        # regardless of what followed, wrongly certifying these as action-led.
        "open source Go PDF manipulation API",
        "open source PDF generation for Go developers",
        "Open source alternative to a commercial library",
        "Open-source document tooling",
    ],
)
def test_open_source_noun_phrase_is_not_action_led(title: str) -> None:
    assert not is_action_led_capability_title(title)


def test_open_as_a_genuine_verb_is_still_action_led() -> None:
    """Negative control: the `open source` exclusion must not blunt real imperative use
    of "open" -- only the specific "open source" collision is excluded."""

    assert is_action_led_capability_title("Open documents and extract text")
    assert is_action_led_capability_title("Open a document from a stream")


def test_pre_fix_open_source_reproduces_the_live_false_positive(monkeypatch) -> None:
    """Negative control for the regex itself: reverting the `(?!\\s+source)` exclusion
    reproduces the exact live misclassification this fix corrects."""

    import re

    import readme_agent.readme.capability_semantics as module

    pre_fix_pattern = module._ACTION_VERBS.pattern.replace("open(?![\\s-]+source)", "open")
    monkeypatch.setattr(module, "_ACTION_VERBS", re.compile(pre_fix_pattern))

    assert module.is_action_led_capability_title("open source PDF generation for Go developers")


def test_capability_rows_are_action_led_matches_the_validator_row_shape() -> None:
    """Compiled-presentation validation reads titles from `- **Title** - ` rows and
    rejects the whole candidate when one is not action-led. The pre-adoption check
    must read exactly that shape, or a block it accepts could still hard-fail."""

    from readme_agent.readme.capability_semantics import capability_rows_are_action_led

    action_led = (
        "- **Convert XLSX files to PDF** - Produce PDF output from workbooks.\n"
        "- **Export STL files** - Write meshes to STL."
    )
    assert capability_rows_are_action_led(action_led)

    # Observed on the Font Python canary: a noun-phrase heading raised
    # "Key capability titles must be action-led search phrases" and skipped the
    # entire repository.
    noun_led = (
        "- **Convert XLSX files to PDF** - Produce PDF output from workbooks.\n"
        "- **Font format conversion support** - Handle font conversions."
    )
    assert not capability_rows_are_action_led(noun_led)


def test_capability_rows_predicate_ignores_non_row_markdown() -> None:
    """Prose that carries no capability rows must not be treated as a violation."""

    from readme_agent.readme.capability_semantics import capability_rows_are_action_led

    assert capability_rows_are_action_led("")
    assert capability_rows_are_action_led("Some introductory sentence.")
