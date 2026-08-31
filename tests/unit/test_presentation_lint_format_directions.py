"""Regressions for a `format_direction_contradiction` false positive found live in
the 2026-08-27 fleet pass: a limitation statement ("Output is limited to PDF
files.") misread as a positive capability claim.

An earlier version of this fix also excluded Markdown table rows from scanning
(reasoning the deterministic API Method Index describes real members, not
visitor-facing promises), but `test_readme_presentation_lint.py::
test_format_direction_lint_rejects_api_name_inference_without_functional_fact`
proved that exclusion wrong: table-row scanning is intentional -- an API
description inferring an unverified format role must still be caught even
inside a table. That part was reverted; only the negation fix below survived
regression testing.
"""

from __future__ import annotations

from readme_agent.readme.presentation_lint_format_directions import (
    directional_fragments,
    lint_format_directions,
)
from tests.unit.test_readme_contextual_links import _verified_facts


def test_limitation_statement_is_not_a_capability_claim():
    """ "Output is limited to PDF files." states a restriction, not a promise --
    the same product.formats fact that forbids PDF output must not flag this as
    the product itself claiming PDF output support."""

    facts = _verified_facts()
    text = "## Limitations\n\n- Output is limited to PDF files.\n"

    assert lint_format_directions(text, facts) == []


def test_genuine_unauthorized_capability_claim_still_blocks():
    """Negative control: a real prose claim asserting the same unauthorized format,
    without restrictive framing, must still be caught."""

    facts = _verified_facts()
    text = "## Key Capabilities\n\n- **Export PDF files** - Convert workbooks to PDF.\n"

    findings = lint_format_directions(text, facts)

    assert any("PDF" in finding.message for finding in findings)


def test_conversion_clause_target_format_is_output_not_input():
    """ "Load a document and convert it to PDF." must attribute PDF to the *output*
    role, not the sentence's earlier "Load" verb -- a conversion clause's target
    format (named after "to"/"into") belongs to the role the conversion produces,
    never to whatever load/read/import verb happens to appear earlier in the same
    sentence. Without a boundary at "convert...to" itself, "Load" (the only
    verb-boundary match) would own the rest of the line and sweep the conversion
    target into an *input* fragment instead -- proven directly by the negative
    control immediately below."""

    line = "Load a document and convert it to PDF."

    fragments = directional_fragments(line)

    input_text = "".join(fragment for role, fragment, _start, _end in fragments if role == "input")
    output_text = "".join(
        fragment for role, fragment, _start, _end in fragments if role == "output"
    )
    assert "PDF" not in input_text
    assert "PDF" in output_text


def test_pre_fix_conversion_clause_reproduces_wrong_input_attribution(monkeypatch):
    """Negative control for the boundary fix: without the "converts...to/into"
    alternative, the same sentence's only verb-boundary match ("Load") owns the
    rest of the line, wrongly sweeping the conversion's real target (PDF) into an
    *input* fragment."""

    import re as _re

    import readme_agent.readme.presentation_lint_format_directions as module

    pre_fix_boundary = _re.compile(
        r"(?i)\b(?:and\s+)?(?:import|load|open|read|export|save|write)s?(?:ing)?\b"
    )
    monkeypatch.setattr(module, "_DIRECTION_BOUNDARY", pre_fix_boundary)

    line = "Load a document and convert it to PDF."
    fragments = module.directional_fragments(line)

    input_text = "".join(fragment for role, fragment, _start, _end in fragments if role == "input")
    assert "PDF" in input_text


def test_generic_any_other_input_hedge_is_not_a_format_claim():
    """PWD-008, live on aspose-words-foss: "A loaded `.md` file converts to DOCX or
    PDF like any other input." wrongly produced an *input*-role finding for
    DOCX/PDF -- not through the boundary mechanism above (past-tense "loaded"
    never matches `_DIRECTION_BOUNDARY` at all, confirmed directly: with every fix
    reverted, this exact sentence produces only the wrong input-role finding, zero
    output-role findings), but through the separate whole-line noun fallback,
    which adds the *entire line* as an input-role fragment purely because the
    unrelated word "input" appears at the end ("like any other input"). The pinned
    fixture authorizes neither format for either role, so the conversion target is
    still genuinely caught once, correctly, as an output-role finding (via the
    boundary fix above) -- the hedge guard's job is only to stop the *second,
    wrong* input-role finding for the same text, proven by the negative control
    immediately below."""

    facts = _verified_facts()
    text = "## Quick Start\n\nA loaded `.md` file converts to DOCX or PDF like any other input.\n"

    findings = lint_format_directions(text, facts)

    assert len(findings) == 1
    assert "output role" in findings[0].message
    assert "input role" not in findings[0].message


def test_pre_fix_hedge_reproduces_the_live_double_finding(monkeypatch):
    """Negative control for the hedge guard: with only `_GENERIC_DIRECTION_HEDGE`
    reverted (boundary fix still active), the exact live sentence produces *two*
    findings -- the correct output-role one and the wrong input-role one, which
    the hedge guard exists to remove."""

    import re as _re

    import readme_agent.readme.presentation_lint_format_directions as module

    monkeypatch.setattr(module, "_GENERIC_DIRECTION_HEDGE", _re.compile(r"(?!)"))

    facts = _verified_facts()
    text = "## Quick Start\n\nA loaded `.md` file converts to DOCX or PDF like any other input.\n"
    findings = module.lint_format_directions(text, facts)

    roles = {"output" if "output role" in f.message else "input" for f in findings}
    assert roles == {"input", "output"}


def test_genuine_input_noun_claim_without_a_hedge_still_blocks():
    """Negative control for the hedge guard: a real, unhedged noun-form input claim
    for the same unauthorized format must still be caught -- the guard must not
    over-suppress every line that happens to contain the word "input"."""

    facts = _verified_facts()
    text = "## Key Capabilities\n\n- **PDF input** - Native PDF input support.\n"

    findings = lint_format_directions(text, facts)

    assert any("PDF" in finding.message and "input" in finding.message for finding in findings)


def test_table_row_format_claims_are_still_caught():
    """An API-reference table row inferring an unauthorized format role must still
    be flagged -- table-row scanning is intentional, not an oversight to exclude."""

    facts = _verified_facts()
    text = (
        "## API Reference\n\n"
        "| Member | Description |\n"
        "| --- | --- |\n"
        "| `PdfSaveOptions(PageIndex, PageCount)` | Configures PDF output through the API. |\n"
    )

    findings = lint_format_directions(text, facts)

    assert any("PDF" in finding.message for finding in findings)
