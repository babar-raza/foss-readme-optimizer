# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_074.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_degenerate_rect_returns_none():

    assert build_appearance("Square", (0, 0, 0, 100), {"C": [0]}) is None