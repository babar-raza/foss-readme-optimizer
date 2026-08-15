# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_080.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_generate_appearance_unsupported_subtype_returns_false():

    doc = _new_page_doc()

    ann = doc.pages[0].annotations.add("Text", (0, 0, 20, 20), "note")

    assert ann.generate_appearance() is False

    assert not ann.has_appearance