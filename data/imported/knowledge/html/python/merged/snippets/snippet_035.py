# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_035.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_border_style_three_tokens() -> None:

    """border-style: solid dashed dotted → top 'solid', right/left 'dashed', bottom 'dotted'."""

    el = _make_element("border-style: solid dashed dotted")

    style = el.get_computed_style()

    assert style.get_property_value("border-top-style") == "solid"

    assert style.get_property_value("border-right-style") == "dashed"

    assert style.get_property_value("border-bottom-style") == "dotted"

    assert style.get_property_value("border-left-style") == "dashed"