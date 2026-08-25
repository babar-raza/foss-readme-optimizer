"""Prove Aspose-link occurrence scanning ignores code-span sample data."""

from __future__ import annotations

from readme_agent.links.occurrences import (
    count_aspose_link_occurrences,
    find_aspose_link_occurrences,
)

_URL = "https://docs.aspose.org/cells/cpp/"


def test_url_inside_fenced_code_block_is_excluded() -> None:
    markdown = (
        "# Product\n\nOpening.\n\n## Quick start\n\n"
        "```cpp\n"
        f'auto link = hyperlinks.Add("A1", 1, 1, "{_URL}");\n'
        "```\n"
    )

    assert find_aspose_link_occurrences(markdown) == []
    assert count_aspose_link_occurrences(markdown).total == 0


def test_url_inside_inline_code_is_excluded() -> None:
    markdown = f"# Product\n\nSee `{_URL}` in the source.\n"

    assert find_aspose_link_occurrences(markdown) == []


def test_url_in_prose_markdown_link_is_still_found() -> None:
    markdown = f"# Product\n\nSee [Docs]({_URL}) for details.\n"

    occurrences = find_aspose_link_occurrences(markdown)

    assert len(occurrences) == 1
    assert occurrences[0].url == _URL
    assert occurrences[0].form == "markdown"


def test_url_in_raw_prose_text_is_still_found() -> None:
    markdown = f"# Product\n\nDocs are at {_URL} directly.\n"

    occurrences = find_aspose_link_occurrences(markdown)

    assert len(occurrences) == 1
    assert occurrences[0].form == "raw"


def test_url_outside_code_span_still_counted_when_the_same_url_also_appears_in_code() -> None:
    """A real prose link is not swallowed just because the same URL is also
    used as sample data elsewhere in a code block."""

    markdown = (
        f"# Product\n\nSee [Docs]({_URL}) for details.\n\n"
        "## Quick start\n\n"
        f'```cpp\nauto link = hyperlinks.Add("A1", 1, 1, "{_URL}");\n```\n'
    )

    occurrences = find_aspose_link_occurrences(markdown)

    assert len(occurrences) == 1
    assert occurrences[0].form == "markdown"
