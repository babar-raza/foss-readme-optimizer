# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_034.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_border_style_four_tokens() -> None:

    """border-style: solid dashed dotted double → all four individually."""

    el = _make_element("border-style: solid dashed dotted double")

    style = el.get_computed_style()

    assert style.get_property_value("border-top-style") == "solid"

    assert style.get_property_value("border-right-style") == "dashed"

    assert style.get_property_value("border-bottom-style") == "dotted"

    assert style.get_property_value("border-left-style") == "double"