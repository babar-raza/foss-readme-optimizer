"""Distinct API member gaps must not read as one repeated limitation."""

from __future__ import annotations

from readme_agent.readme.presentation_lint_semantics import lint_semantics

_RULE = "The same visitor-facing limitation is expressed more than once."


def _limitation_findings(markdown: str) -> list[str]:
    return [finding.message for finding in lint_semantics(markdown, None)]


def _document(bullets: str) -> str:
    return f"""# Product

## Scope and Limitations

The library targets the workflows listed above.

### API Member Gaps

{bullets}
"""


def test_distinct_members_sharing_a_method_name_are_not_one_limitation() -> None:
    """PF05 BarCode canary: `Gs1Helper.validate` and `EciHelper.validate` are two
    different unimplemented members. Bullet normalization casefolds and rewrites
    `.` to a space, so only the digit-bearing name kept a discriminator and the
    "both non-empty" guard never fired."""

    markdown = _document(
        "- `Gs1Helper.validate` is not implemented in this FOSS package.\n"
        "- `EciHelper.validate` is not implemented in this FOSS package."
    )

    assert _RULE not in _limitation_findings(markdown)


def test_genuinely_repeated_limitation_is_still_reported() -> None:
    """The fix must not disable the rule: an actually repeated constraint still fires."""

    markdown = _document(
        "- PDF export is not implemented in this FOSS package.\n"
        "- PDF export is not available in this FOSS package."
    )

    assert _RULE in _limitation_findings(markdown)


def test_symbology_numbers_still_separate_near_identical_constraints() -> None:
    """The previously documented Code 128 / Code 39 discrimination is preserved."""

    markdown = _document(
        "- Only the SVG backend is implemented for Code 128.\n"
        "- Only the SVG backend is implemented for Code 39."
    )

    assert _RULE not in _limitation_findings(markdown)
