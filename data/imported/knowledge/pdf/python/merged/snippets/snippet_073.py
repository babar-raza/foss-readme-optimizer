# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_073.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_missing_geometry_returns_none():

    assert build_appearance("Line", (0, 0, 100, 100), {}) is None

    assert build_appearance("Ink", (0, 0, 100, 100), {}) is None

    assert build_appearance("Highlight", (0, 0, 100, 100), {}) is None