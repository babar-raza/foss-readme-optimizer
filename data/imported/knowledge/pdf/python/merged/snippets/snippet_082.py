# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_082.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_page_generate_appearances_counts_created():

    doc = _new_page_doc()

    page = doc.pages[0]

    page.annotations.add("Square", (0, 0, 50, 50), "")

    page.annotations.add("Circle", (60, 0, 110, 50), "")

    page.annotations.add("Text", (0, 60, 20, 80), "")  # unsupported -> skipped

    assert page.annotations.generate_appearances() == 2