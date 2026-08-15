# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_041.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_css_supports_border_style() -> None:

    """CSS.supports('border-style', 'solid') returns True (AC-9)."""

    assert CSS.supports("border-style", "solid") is True