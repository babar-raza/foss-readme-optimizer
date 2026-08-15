# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_032.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_border_style_single_token() -> None:

    """border-style: solid broadcasts to all four border-*-style longhands (AC-4)."""

    el = _make_element("border-style: solid")

    style = el.get_computed_style()

    assert style.get_property_value("border-top-style") == "solid"

    assert style.get_property_value("border-right-style") == "solid"

    assert style.get_property_value("border-bottom-style") == "solid"

    assert style.get_property_value("border-left-style") == "solid"