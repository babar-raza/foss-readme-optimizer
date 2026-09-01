"""Prove limitation_phrases() accepts safe visitor-facing markdown while still
rejecting raw internal-artifact literals (PWD-048)."""

from readme_agent.facts.limitation_rendering import limitation_phrases


def test_markdown_link_in_a_limitation_is_not_treated_as_a_raw_literal() -> None:
    """PWD-048: `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`'s real, only
    `product.limitations` entry -- "3MF import/export (`ThreeMfImporter`/
    `ThreeMfExporter`) requires the `adm-zip` package at runtime -- see
    [upstream-issues.md](upstream-issues.md) for a real packaging gap that
    affects consumers of the published package." -- was treated as malformed
    because its own markdown link's `[text](target)` brackets tripped the
    `{}[]` raw-list/dict-literal exclusion, making `limitation_phrases()`
    return `[]` for the WHOLE list and cascading into `public_limitation_
    phrases()` returning `[]` too -- which `verified_limitations_are_
    represented()` treats as "no limitation exists to represent at all",
    even though this is a real, verified, public-safe constraint."""

    statement = (
        "3MF import/export (`ThreeMfImporter`/`ThreeMfExporter`) requires the "
        "`adm-zip` package at runtime -- see [upstream-issues.md](upstream-issues.md) "
        "for a real packaging gap that affects consumers of the published package."
    )

    assert limitation_phrases([statement]) == [statement]


def test_raw_list_literal_is_still_rejected_as_malformed() -> None:
    """Negative control: a genuine internal artifact -- a Python-repr list
    dump, not a markdown link -- must still make the whole list malformed.
    Proves the fix narrows the exemption to real markdown links only,
    rather than loosening the `{}[]` check generally."""

    statement = "Supported output formats: ['PDF', 'DOCX']"

    assert limitation_phrases([statement]) == []


def test_raw_dict_literal_is_still_rejected_as_malformed() -> None:
    statement = "Unsupported options: {'password': True}"

    assert limitation_phrases([statement]) == []


def test_bracket_without_a_markdown_link_target_is_still_rejected() -> None:
    """A bare `[TODO]`-style annotation has no `](target)` following it, so it
    is not a markdown link and must not be exempted."""

    statement = "Streaming export is not supported [TODO]."

    assert limitation_phrases([statement]) == []
