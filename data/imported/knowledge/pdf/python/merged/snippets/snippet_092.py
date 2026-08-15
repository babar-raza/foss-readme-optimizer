# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_092.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_freetext_da_quadding_roundtrip():

    doc, page = _new_page()

    page.annotations.add(

        "FreeText",

        (10, 10, 200, 40),

        "hi",

        properties={"DA": "0 0 1 rg /Helv 12 Tf", "Q": 1},

    )

    a = _roundtrip(doc).pages[0].annotations[0]

    assert a.get_property("DA") == "0 0 1 rg /Helv 12 Tf"

    assert a.get_property("Q") == 1