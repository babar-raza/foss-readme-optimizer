# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_095.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_set_property_update_and_delete():

    doc, page = _new_page()

    ann = page.annotations.add("Square", (0, 0, 50, 50), "x", properties={"C": [1, 0, 0]})

    ann.set_property("IC", [0, 0, 1])

    assert page.annotations[0].get_property("IC") == [0, 0, 1]

    ann.set_property("C", None)  # delete

    assert "C" not in page.annotations[0].properties



    a = _roundtrip(doc).pages[0].annotations[0]

    assert a.get_property("IC") == [0, 0, 1]

    assert "C" not in a.properties