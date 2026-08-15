# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_052.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_polygon_cloud_border():

    gen = build_appearance(

        "Polygon",

        _RECT,

        {"Vertices": [10, 10, 110, 10, 60, 70], "C": [0, 0, 0], "BE": {"S": N("C"), "I": 1}},

    )

    assert gen is not None

    assert b" c\n" in gen.content