# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_083.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_document_generate_appearances_across_pages():

    doc = Document()

    doc.pages.add()

    doc.pages.add()

    doc.pages[0].annotations.add("Square", (0, 0, 50, 50), "")

    doc.pages[1].annotations.add(

        "Line", (0, 0, 50, 50), "", properties={"L": [0, 0, 50, 50]}

    )

    assert doc.generate_appearances() == 2

    # Second call is a no-op (appearances already present).

    assert doc.generate_appearances() == 0