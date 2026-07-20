from dataclasses import dataclass

from readme_agent.readme.presentation_report import detect_presentation, product_explanation_offset

# Verified against the three real pilot READMEs (cells/java, pdf/java,
# 3d/java) before this module shipped -- see presentation_report.py's
# _CONCRETE_PHRASES comment for why "library for"/"working with"/
# "implementation of" are included, not just bare verbs.
GOOD_OPENING = (
    "# Example FOSS\n\n"
    "Example FOSS is a Java library for creating, reading, and modifying "
    "spreadsheet files.\n\n"
    "## Features\n\n- one\n"
)
NAME_ONLY_OPENING = "# Example FOSS\n\nExample FOSS.\n\n## Features\n\n- one\n"
NO_HEADING_SKIP = (
    "# Example FOSS\n\n"
    "Example FOSS is a Java library for creating, reading, and modifying files.\n\n"
    "## Features\n\n### Details\n\n- one\n"
)
HEADING_SKIP = (
    "# Example FOSS\n\n"
    "Example FOSS is a Java library for creating, reading, and modifying files.\n\n"
    "### Skipped H2\n\n- one\n"
)
ONE_EXAMPLE = "# X\n\n```python\ncode()\n```\n"
TWO_EXAMPLES = "# X\n\n```python\ncode()\n```\n\nMore.\n\n```python\nmore_code()\n```\n"


class TestProductExplanationOffset:
    def test_finds_offset_of_the_explaining_line(self):
        offset = product_explanation_offset(GOOD_OPENING)
        assert offset is not None
        assert GOOD_OPENING[offset:].startswith("Example FOSS is a Java library")

    def test_none_when_opening_is_name_only(self):
        assert product_explanation_offset(NAME_ONLY_OPENING) is None


class TestDetectPresentation:
    def test_explains_product_in_opening(self):
        report = detect_presentation(GOOD_OPENING)
        assert report.explains_product_in_opening

    def test_does_not_explain_product_when_opening_is_name_only(self):
        report = detect_presentation(NAME_ONLY_OPENING)
        assert not report.explains_product_in_opening
        assert "explains_product_in_opening" in report.diagnostic_gaps

    def test_states_ecosystem_when_platform_keyword_present(self):
        report = detect_presentation(GOOD_OPENING, platform="java")
        assert report.states_audience_or_ecosystem

    def test_heading_levels_consistent_when_no_skip(self):
        assert detect_presentation(NO_HEADING_SKIP).heading_levels_consistent

    def test_heading_levels_inconsistent_when_h1_jumps_to_h3(self):
        report = detect_presentation(HEADING_SKIP)
        assert not report.heading_levels_consistent
        assert "H1->H3" in (report.evidence["heading_levels_consistent"] or "")

    def test_no_runnable_example_with_one_fenced_block(self):
        assert not detect_presentation(ONE_EXAMPLE).has_runnable_example

    def test_runnable_example_with_two_fenced_blocks(self):
        assert detect_presentation(TWO_EXAMPLES).has_runnable_example

    def test_install_path_not_checked_without_a_resolver(self):
        report = detect_presentation(GOOD_OPENING, ecosystem="maven", manifest={"group_id": "x"})
        assert report.install_path_resolved is None
        assert "install_path_resolved" not in report.diagnostic_gaps

    def test_install_path_resolved_true_when_resolver_finds_it(self):
        @dataclass
        class FakeResult:
            found: bool
            detail: str

        report = detect_presentation(
            GOOD_OPENING,
            ecosystem="maven",
            manifest={"group_id": "org.aspose", "artifact_id": "aspose-pdf"},
            resolver=lambda eco, man: FakeResult(True, "found"),
        )
        assert report.install_path_resolved is True

    def test_install_path_resolved_false_surfaces_as_a_diagnostic_gap(self):
        """Models the real cells-java finding: a resolver that reports NOT
        FOUND must show up in diagnostic_gaps, not be silently swallowed."""

        @dataclass
        class FakeResult:
            found: bool
            detail: str

        report = detect_presentation(
            GOOD_OPENING,
            ecosystem="maven",
            manifest={"group_id": "org.aspose", "artifact_id": "aspose-cells-foss"},
            resolver=lambda eco, man: FakeResult(False, "NOT FOUND (0 results)"),
        )
        assert report.install_path_resolved is False
        assert "install_path_resolved" in report.diagnostic_gaps
