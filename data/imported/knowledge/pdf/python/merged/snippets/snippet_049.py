# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_049.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_polyline_endings_orient_to_end_edges():

    gen = build_appearance(

        "PolyLine",

        _RECT,

        {"Vertices": [10, 10, 60, 60, 110, 10], "LE": [N("OpenArrow"), N("OpenArrow")]},

    )

    assert gen is not None

    # Shaft stroke plus one stroke per open-arrow head.

    assert gen.content.count(b"\nS\n") == 3