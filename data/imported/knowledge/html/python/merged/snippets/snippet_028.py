# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_028.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_border_width_single_token() -> None:

    """border-width: 2px broadcasts to all four border-*-width longhands (AC-1)."""

    el = _make_element("border-width: 2px")

    style = el.get_computed_style()

    assert style.get_property_value("border-top-width") == "2px"

    assert style.get_property_value("border-right-width") == "2px"

    assert style.get_property_value("border-bottom-width") == "2px"

    assert style.get_property_value("border-left-width") == "2px"