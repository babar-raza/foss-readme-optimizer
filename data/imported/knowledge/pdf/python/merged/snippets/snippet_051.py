# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_051.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_square_without_be_stays_rectangular():

    gen = build_appearance("Square", _RECT, {"C": [0, 0, 0], "BS": {"W": 1}})

    assert b" re" in gen.content

    assert b" c\n" not in gen.content