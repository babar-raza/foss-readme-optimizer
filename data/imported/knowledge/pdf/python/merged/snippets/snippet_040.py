# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_040.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_dash_from_border_style_array():

    gen = build_appearance(

        "Square", _RECT, {"C": [0, 0, 0], "BS": {"S": N("D"), "D": [3, 2], "W": 2}}

    )

    assert gen is not None

    assert b"[3 2] 0 d" in gen.content