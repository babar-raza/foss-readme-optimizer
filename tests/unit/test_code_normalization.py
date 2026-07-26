"""Unit tests for generated source-code normalization."""

from readme_agent.facts.code_normalization import normalize_generated_code


def test_normalizes_typographic_quote_delimiters_to_ascii() -> None:
    source = "var node = scene.CreateChildNode(\u201cBox\u201d); value = \u2018x\u2019;"

    assert normalize_generated_code(source) == (
        "var node = scene.CreateChildNode(\"Box\"); value = 'x';"
    )


def test_preserves_already_ascii_source_byte_for_byte() -> None:
    source = 'var node = scene.CreateChildNode("Box");'

    assert normalize_generated_code(source) == source
