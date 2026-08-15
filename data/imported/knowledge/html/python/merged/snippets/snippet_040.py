# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_040.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_css_supports_border_width() -> None:

    """CSS.supports('border-width', '1px') returns True (AC-8)."""

    assert CSS.supports("border-width", "1px") is True