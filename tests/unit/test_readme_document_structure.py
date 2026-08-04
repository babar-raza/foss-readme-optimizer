"""Focused tests for the extracted markdown-structure module."""

from readme_agent.readme.document_structure import (
    github_anchor,
    introduced_duplicate_headings,
    line_offsets,
    normalize_navigation_targets,
    parse_headings,
    rebuild_navigation_for_labels,
    remove_redundant_nested_headings,
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


def test_navigation_can_be_rebuilt_from_final_labels_not_local_headings() -> None:
    markdown = "## Navigation\n\n- [Old](#old)\n\n## At a glance\n\nSummary.\n"

    normalized = rebuild_navigation_for_labels(
        markdown,
        ["At a glance", "Usage", "License"],
    )

    assert "- [At a glance](#at-a-glance)" in normalized
    assert "- [Usage](#usage)" in normalized
    assert "- [License](#license)" in normalized
    assert "- [Old](#old)" not in normalized


def test_redundant_nested_heading_is_removed_and_children_are_promoted() -> None:
    markdown = (
        "# Widget\n\n## Examples\n\n### Examples\n\n#### Parse a file\n\nRun it.\n\n## License\n"
    )

    normalized = remove_redundant_nested_headings(markdown)

    assert normalized.count("Examples") == 1
    assert "### Parse a file" in normalized
    assert "#### Parse a file" not in normalized
    assert "## License" in normalized


def test_duplicate_heading_control_ignores_fences_and_existing_source_multiplicity() -> None:
    source = "# Widget\n\n## Examples\n\n### Quick Start\n"
    candidate = source + "\n```markdown\n### Quick Start\n```\n"

    assert introduced_duplicate_headings(source, candidate) == []
    assert introduced_duplicate_headings(
        source,
        candidate + "\n### Quick Start\n",
    ) == ["h3 quick-start"]


def test_duplicate_heading_identity_is_global_across_heading_levels() -> None:
    assert introduced_duplicate_headings("", "## Quick start\n\n### Quick Start\n") == [
        "h2/h3 quick-start"
    ]
    assert introduced_duplicate_headings(
        "## Quick start\n",
        "## Quick start\n\n### Quick Start\n",
    ) == ["h2/h3 quick-start"]
    assert introduced_duplicate_headings("", "# A\n\n## API\n\n### API\n") == ["h2/h3 api"]


def test_duplicate_heading_identity_preserves_source_multiplicity_and_distinct_titles() -> None:
    existing_collision = "## Quick start\n\n### Quick Start\n"

    assert introduced_duplicate_headings(existing_collision, existing_collision) == []
    assert introduced_duplicate_headings("", "## API\n\n### Reference\n") == []
