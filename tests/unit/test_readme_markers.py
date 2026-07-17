from readme_agent.readme.markers import find_span, remove_span, upsert_span

SAMPLE_README = """# Aspose.Example FOSS for Java

A short intro paragraph.

## Features

- one
- two
"""


class TestCalloutInsertion:
    def test_inserts_right_after_h1(self):
        result = upsert_span(SAMPLE_README, "callout", "some callout text", "abc123")

        assert "# Aspose.Example FOSS for Java" in result
        h1_idx = result.index("# Aspose.Example FOSS for Java")
        callout_idx = result.index("readme-agent:callout ")
        features_idx = result.index("## Features")
        assert h1_idx < callout_idx < features_idx

    def test_never_touches_content_outside_the_span(self):
        result = upsert_span(SAMPLE_README, "callout", "some callout text", "abc123")
        assert "A short intro paragraph." in result
        assert "## Features" in result
        assert "- one\n- two" in result


class TestResourcesInsertion:
    def test_appends_at_end_of_file(self):
        result = upsert_span(SAMPLE_README, "resources", "some resources text", "abc123")
        assert result.rstrip().endswith("readme-agent:resources:end -->")
        assert result.startswith("# Aspose.Example FOSS for Java")


class TestFindAndReplace:
    def test_find_span_returns_none_when_absent(self):
        assert find_span(SAMPLE_README, "callout") is None

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

    def test_callout_and_resources_are_independent_spans(self):
        with_callout = upsert_span(SAMPLE_README, "callout", "callout content", "111aaa")
        with_both = upsert_span(with_callout, "resources", "resources content", "222bbb")

        assert find_span(with_both, "callout").content == "callout content"
        assert find_span(with_both, "resources").content == "resources content"


class TestRemoveSpan:
    def test_remove_span_restores_original_content(self):
        with_span = upsert_span(SAMPLE_README, "resources", "content", "aaa111")
        removed = remove_span(with_span, "resources")
        assert removed == SAMPLE_README

    def test_remove_absent_span_is_a_noop(self):
        assert remove_span(SAMPLE_README, "callout") == SAMPLE_README

    def test_removing_both_spans_in_either_order_restores_original(self):
        with_both = upsert_span(
            upsert_span(SAMPLE_README, "callout", "callout content", "aaa111"),
            "resources",
            "resources content",
            "bbb222",
        )

        order_a = remove_span(remove_span(with_both, "callout"), "resources")
        order_b = remove_span(remove_span(with_both, "resources"), "callout")

        assert order_a == SAMPLE_README
        assert order_b == SAMPLE_README


class TestNoH1:
    def test_callout_inserts_at_top_when_no_h1(self):
        text = "Just some text with no heading.\n"
        result = upsert_span(text, "callout", "content", "aaa111")
        assert result.startswith("\n<!-- readme-agent:callout") or result.index(
            "readme-agent:callout"
        ) < result.index("Just some text")
