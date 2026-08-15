# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_078.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_stamp_generate_appearance_end_to_end():

    doc = _new_page_doc()

    ann = doc.pages[0].annotations.add(

        "Stamp",

        (100, 100, 260, 150),

        "",

        properties={"Name": AnnotationName("Approved")},

    )

    assert ann.generate_appearance() is True

    assert b"(APPROVED) Tj" in ann.appearance_normal