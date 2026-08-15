# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_090.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ink_nested_list_roundtrip():

    doc, page = _new_page()

    ink = [[10, 10, 20, 20, 30, 10], [40, 40, 50, 50]]

    page.annotations.add("Ink", (10, 10, 60, 60), "", properties={"InkList": ink})

    a = _roundtrip(doc).pages[0].annotations[0]

    assert a.subtype == "Ink"

    assert a.get_property("InkList") == ink