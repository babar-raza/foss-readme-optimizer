# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_044.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_border_top_shorthand_regression() -> None:

    """border-top: 1px dashed blue still expands to its three longhands."""

    el = _make_element("border-top: 1px dashed blue")

    style = el.get_computed_style()

    assert style.get_property_value("border-top-width") == "1px"

    assert style.get_property_value("border-top-style") == "dashed"

    assert style.get_property_value("border-top-color") == "blue"