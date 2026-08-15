# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_042.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_solid_border_emits_no_dash():

    gen = build_appearance("Square", _RECT, {"C": [0, 0, 0], "BS": {"W": 1}})

    assert b" d\n" not in gen.content