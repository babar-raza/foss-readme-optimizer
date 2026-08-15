# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_085.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_flatten_generates_and_inlines_missing_appearance():

    doc = _new_page_doc()

    doc.pages[0].annotations.add(

        "Square", (100, 100, 200, 200), "", properties={"C": [0, 0, 0]}

    )

    before = doc._engine_pdf.page_contents[0]

    doc.flatten()

    after = doc._engine_pdf.page_contents[0]

    assert len(after) > len(before)

    assert b"Do" in after

    assert len(doc._engine_pdf.get_annotations(0)) == 0