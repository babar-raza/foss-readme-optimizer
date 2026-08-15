# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_072.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_unsupported_subtype_returns_none():

    assert build_appearance("Text", (0, 0, 20, 20), {}) is None

    assert build_appearance("Popup", (0, 0, 20, 20), {}) is None

    assert build_appearance("Widget", (0, 0, 20, 20), {}) is None