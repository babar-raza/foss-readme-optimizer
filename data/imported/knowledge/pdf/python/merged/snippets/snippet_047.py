# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_047.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_line_diamond_and_circle_endings():

    diamond = build_appearance(

        "Line", _RECT, {"L": [10, 40, 100, 40], "LE": [N("Diamond"), N("None")]}

    )

    assert b"\nb\n" in diamond.content

    circle = build_appearance(

        "Line", _RECT, {"L": [10, 40, 100, 40], "LE": [N("None"), N("Circle")]}

    )

    assert circle.content.count(b" c") == 4  # four Bézier arcs
