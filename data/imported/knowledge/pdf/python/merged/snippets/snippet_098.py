# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_098.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_enum_accepted_as_subtype():

    doc, page = _new_page()

    page.annotations.add(

        AnnotationType.POLYGON,

        (0, 0, 10, 10),

        "",

        properties={"Vertices": [0, 0, 10, 0, 5, 10]},

    )

    a = _roundtrip(doc).pages[0].annotations[0]

    assert a.subtype == "Polygon"

    assert a.get_property("Vertices") == [0, 0, 10, 0, 5, 10]