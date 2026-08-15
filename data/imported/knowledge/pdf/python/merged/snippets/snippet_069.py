# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_069.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_stamp_honours_colour_and_contents_fallback():

    gen = build_appearance(

        "Stamp", (0, 0, 120, 40), {"C": [0, 0, 1], "Contents": "Reviewed"}

    )

    assert gen is not None

    assert b"0 0 1 RG" in gen.content and b"0 0 1 rg" in gen.content

    assert b"(Reviewed) Tj" in gen.content  # falls back to /Contents
