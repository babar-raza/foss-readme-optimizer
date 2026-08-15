# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_039.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_border_color_three_tokens() -> None:

    """border-color: red green blue → top 'red', right/left 'green', bottom 'blue'."""

    el = _make_element("border-color: red green blue")

    style = el.get_computed_style()

    assert style.get_property_value("border-top-color") == "red"

    assert style.get_property_value("border-right-color") == "green"

    assert style.get_property_value("border-bottom-color") == "blue"

    assert style.get_property_value("border-left-color") == "green"