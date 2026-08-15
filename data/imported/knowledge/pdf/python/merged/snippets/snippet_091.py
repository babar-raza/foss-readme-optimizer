# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_091.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_name_marker_roundtrip_and_equality():

    doc, page = _new_page()

    page.annotations.add(

        "Text",

        (10, 10, 30, 30),

        "note",

        properties={"Name": Name("Comment"), "Open": True},

    )

    a = _roundtrip(doc).pages[0].annotations[0]

    name = a.get_property("Name")

    assert name == "Comment"  # equality with a plain str still holds

    assert isinstance(name, Name)  # but it is still marked as a PDF name

    assert a.get_property("Open") is True