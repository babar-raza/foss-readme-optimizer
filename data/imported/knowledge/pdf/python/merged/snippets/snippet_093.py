# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_093.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_stamp_name_roundtrip():

    doc, page = _new_page()

    page.annotations.add(

        "Stamp", (10, 10, 110, 60), "", properties={"Name": Name("Approved")}

    )

    a = _roundtrip(doc).pages[0].annotations[0]

    assert a.subtype == "Stamp"

    assert a.get_property("Name") == "Approved"