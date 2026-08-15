# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_041.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_dash_style_d_without_array_defaults():

    gen = build_appearance(

        "Square", _RECT, {"C": [0, 0, 0], "BS": {"S": N("D"), "W": 1}}

    )

    assert b"[3] 0 d" in gen.content