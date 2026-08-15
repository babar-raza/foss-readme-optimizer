# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_071.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_caret_honours_rgb_colour():

    gen = build_appearance("Caret", (0, 0, 20, 20), {"C": [1, 0, 0]})

    assert gen is not None

    assert b"1 0 0 rg" in gen.content