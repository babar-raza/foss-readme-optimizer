# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_045.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_line_open_arrow_end_adds_strokes():

    plain = build_appearance("Line", _RECT, {"L": [10, 40, 100, 40], "C": [0, 0, 0]})

    arrow = build_appearance(

        "Line",

        _RECT,

        {"L": [10, 40, 100, 40], "C": [0, 0, 0], "LE": [N("None"), N("OpenArrow")]},

    )

    # The arrowhead adds two more line segments and a stroke beyond the shaft.

    assert arrow.content.count(b" l") > plain.content.count(b" l")

    assert arrow.content.count(b"\nS\n") == 2  # shaft + arrowhead
