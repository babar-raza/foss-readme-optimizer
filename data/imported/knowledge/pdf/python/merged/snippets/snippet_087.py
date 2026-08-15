# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_087.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_line_properties_roundtrip():

    doc, page = _new_page()

    page.annotations.add(

        "Line",

        (10, 10, 200, 60),

        "measure",

        properties={

            "L": [10, 20, 200, 50],

            "LE": [Name("OpenArrow"), Name("None")],

            "C": [1, 0, 0],

        },

    )

    a = _roundtrip(doc).pages[0].annotations[0]

    assert a.subtype == "Line"

    assert a.get_property("L") == [10, 20, 200, 50]

    assert a.get_property("LE") == ["OpenArrow", "None"]

    assert a.color == (1.0, 0.0, 0.0)