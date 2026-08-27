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

from readme_agent.readme.presentation_lint_format_directions import lint_format_directions
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
