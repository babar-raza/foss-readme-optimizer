# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_097.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_markup_subclass_wrapping():

    doc, page = _new_page()

    page.annotations.add("Highlight", (0, 0, 10, 10), "")

    assert isinstance(page.annotations[0], MarkupAnnotation)