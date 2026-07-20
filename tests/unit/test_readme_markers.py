import pytest

from readme_agent.readme.markers import find_span, remove_span, render_span, upsert_span

SAMPLE_README = """# Aspose.Example FOSS for Java

A short intro paragraph.

## Features

- one
- two
"""


def _legacy_callout_text(base: str, content: str, facts_hash: str) -> str:
    """Builds text with a manually-constructed "callout" span, right after the
    H1 -- exactly the shape a pre-Phase-21 work clone has on disk. Deliberately
    NOT built via upsert_span, which no longer accepts "callout" (see
    TestCalloutRetired) -- this simulates legacy content for migration tests."""
    h1_end = base.index("\n", base.index("# ")) + 1
    rendered = render_span("callout", content, facts_hash)
    return base[:h1_end] + "\n" + rendered + "\n" + base[h1_end:]


class TestCalloutRetired:
    """Phase 21 (decision #9 as corrected): callout is retired. upsert_span
    must reject it outright -- the only way a callout span can exist in text
    this codebase touches is as legacy content to be stripped, never inserted."""

    def test_upsert_span_rejects_callout(self):
        with pytest.raises(ValueError, match="callout"):
            upsert_span(SAMPLE_README, "callout", "content", "abc123")

    def test_remove_span_strips_a_legacy_callout_cleanly(self):
        with_legacy_callout = _legacy_callout_text(SAMPLE_README, "old callout content", "aaa111")
        assert "readme-agent:callout" in with_legacy_callout

        removed = remove_span(with_legacy_callout, "callout")
        assert removed == SAMPLE_README

    def test_find_span_still_recognizes_a_legacy_callout(self):
        with_legacy_callout = _legacy_callout_text(SAMPLE_README, "old callout content", "aaa111")
        match = find_span(with_legacy_callout, "callout")
        assert match is not None
        assert match.content == "old callout content"


class TestResourcesInsertion:
    def test_appends_at_end_of_file(self):
        result = upsert_span(SAMPLE_README, "resources", "some resources text", "abc123")
        assert result.rstrip().endswith("readme-agent:resources:end -->")
        assert result.startswith("# Aspose.Example FOSS for Java")

    def test_never_touches_content_outside_the_span(self):
        result = upsert_span(SAMPLE_README, "resources", "some resources text", "abc123")
        assert "A short intro paragraph." in result
        assert "## Features" in result
        assert "- one\n- two" in result


class TestFindAndReplace:
    def test_find_span_returns_none_when_absent(self):
        assert find_span(SAMPLE_README, "resources") is None

    def test_upsert_then_find_roundtrips_hash_and_content(self):
        result = upsert_span(SAMPLE_README, "resources", "content here", "deadbeef")
        match = find_span(result, "resources")
        assert match is not None
        assert match.facts_hash == "deadbeef"
        assert match.schema_version == "2"
        assert match.content == "content here"

    def test_upsert_replaces_existing_span_not_duplicates(self):
        once = upsert_span(SAMPLE_README, "resources", "first version", "aaa111")
        twice = upsert_span(once, "resources", "second version", "bbb222")

        assert twice.count("readme-agent:resources ") == 1
        match = find_span(twice, "resources")
        assert match is not None
        assert match.content == "second version"
        assert match.facts_hash == "bbb222"


class TestRemoveSpan:
    def test_remove_span_restores_original_content(self):
        with_span = upsert_span(SAMPLE_README, "resources", "content", "aaa111")
        removed = remove_span(with_span, "resources")
        assert removed == SAMPLE_README

    def test_remove_absent_span_is_a_noop(self):
        assert remove_span(SAMPLE_README, "resources") == SAMPLE_README

    def test_removing_a_legacy_callout_and_a_real_resources_span_restores_original(self):
        """The exact shape orchestrator.py's migration step encounters: a
        legacy callout plus a properly-upserted resources span, in one
        work-clone README, both must strip cleanly regardless of order."""
        with_callout = _legacy_callout_text(SAMPLE_README, "callout content", "aaa111")
        with_both = upsert_span(with_callout, "resources", "resources content", "bbb222")

        order_a = remove_span(remove_span(with_both, "callout"), "resources")
        order_b = remove_span(remove_span(with_both, "resources"), "callout")

        assert order_a == SAMPLE_README
        assert order_b == SAMPLE_README
