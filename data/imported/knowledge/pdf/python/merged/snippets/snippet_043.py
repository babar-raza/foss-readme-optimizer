# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_043.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_dash_from_legacy_border_array():

    gen = build_appearance(

        "Circle", _RECT, {"C": [0, 0, 0], "Border": [0, 0, 1, [2, 2]]}

    )

    assert b"[2 2] 0 d" in gen.content