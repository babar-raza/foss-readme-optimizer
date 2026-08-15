# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_089.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_polygon_polyline_vertices_roundtrip():

    doc, page = _new_page()

    verts = [10, 10, 100, 10, 55, 90]

    page.annotations.add(

        "Polygon", (10, 10, 100, 90), "", properties={"Vertices": verts, "IC": [0, 1, 0]}

    )

    page.annotations.add(

        "PolyLine", (10, 10, 100, 90), "", properties={"Vertices": verts}

    )

    page2 = _roundtrip(doc).pages[0]

    assert page2.annotations[0].get_property("Vertices") == verts

    assert page2.annotations[0].get_property("IC") == [0, 1, 0]

    assert page2.annotations[1].subtype == "PolyLine"

    assert page2.annotations[1].get_property("Vertices") == verts