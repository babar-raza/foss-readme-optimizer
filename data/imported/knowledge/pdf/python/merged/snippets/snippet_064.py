# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_064.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_freetext_fills_background_from_c():

    gen = build_appearance(

        "FreeText", (0, 0, 100, 40), {"Contents": "hi", "C": [1, 1, 0]}

    )

    assert gen is not None

    assert b"1 1 0 rg" in gen.content  # yellow background fill

    assert b"\nf\n" in gen.content