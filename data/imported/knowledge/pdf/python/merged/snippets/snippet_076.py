# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_076.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_highlight_generate_appearance_has_extgstate_resource():

    doc = _new_page_doc()

    ann = doc.pages[0].annotations.add(

        "Highlight",

        (100, 100, 300, 140),

        "",

        properties={"QuadPoints": [100, 140, 300, 140, 100, 100, 300, 100]},

    )

    assert ann.generate_appearance() is True

    assert b"/GsMul gs" in ann.appearance_normal