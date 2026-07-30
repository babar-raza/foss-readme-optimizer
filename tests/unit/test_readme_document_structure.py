"""Focused tests for the extracted markdown-structure module."""

from readme_agent.readme.document_structure import (
    github_anchor,
    line_offsets,
    normalize_navigation_targets,
    parse_headings,
)


class TestLineOffsets:
    def test_cumulative_byte_offsets_include_newlines(self):
        assert line_offsets("a\nbb\nccc") == [0, 2, 5, 8]

    def test_empty_text(self):
        assert line_offsets("") == [0]


class TestParseHeadings:
    def test_levels_titles_and_section_bounds(self):
        text = "# Title\n\n## First\n\nbody\n\n## Second\n\nmore\n"
        headings = parse_headings(text)
        assert [(h.level, h.title) for h in headings] == [
            (1, "Title"),
            (2, "First"),
            (2, "Second"),
        ]
        title, first, second = headings
        # H1 has no later same-or-higher heading -> its section runs to the end.
        assert title.section_end == len(text)
        # "First" ends exactly where "Second" begins.
        assert first.section_end == second.start
        assert second.section_end == len(text)

    def test_nested_section_end_stops_at_next_same_or_higher_level(self):
        text = "## Parent\n\n### Child\n\n## Sibling\n"
        parent, child, sibling = parse_headings(text)
        # Parent (h2) is not swallowed by Child (h3); it ends at the h2 Sibling.
        assert parent.section_end == sibling.start
        # Child (h3) ends at the higher-level Sibling (h2).
        assert child.section_end == sibling.start

    def test_no_headings_returns_empty(self):
        assert parse_headings("just prose, no headings\n") == []


class TestGithubAnchor:
    def test_lowercases_and_hyphenates(self):
        assert github_anchor("Quick Start") == "quick-start"

    def test_strips_punctuation_and_collapses_separators(self):
        assert github_anchor("C++ & Go") == "c-go"

    def test_trims_leading_and_trailing_separators(self):
        assert github_anchor("  Hello!  ") == "hello"


def test_navigation_normalization_preserves_an_opaque_batch_boundary() -> None:
    markdown = (
        "# Widget\n\n"
        "## Navigation\n\n"
        "- [Wrong](#wrong)\n\n"
        "README_AGENT_FIDELITY_BOUNDARY_0001\n"
        "## Usage\n\n"
        "Run it.\n"
    )

    normalized = normalize_navigation_targets(
        markdown,
        boundary_line_prefix="README_AGENT_FIDELITY_BOUNDARY_",
    )

    assert "README_AGENT_FIDELITY_BOUNDARY_0001" in normalized
    assert "- [Usage](#usage)" in normalized
