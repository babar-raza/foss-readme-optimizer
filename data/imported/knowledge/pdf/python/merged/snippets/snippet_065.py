# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_065.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_freetext_uses_default_appearance_size_and_colour():

    gen = build_appearance(

        "FreeText", (0, 0, 200, 30), {"Contents": "hi", "DA": "/Helv 14 Tf 1 0 0 rg"}

    )

    assert gen is not None

    assert b"/Helv 14 Tf" in gen.content

    assert b"1 0 0 rg" in gen.content