# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_046.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_line_closed_arrow_is_filled():

    gen = build_appearance(

        "Line",

        _RECT,

        {"L": [10, 40, 100, 40], "C": [1, 0, 0], "LE": [N("None"), N("ClosedArrow")]},

    )

    assert b"\nb\n" in gen.content  # closepath-fill-stroke triangle

    assert b"1 0 0 rg" in gen.content  # filled with the line colour
