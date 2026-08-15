# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_068.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_stamp_draws_named_caption_in_red_by_default():

    gen = build_appearance(

        "Stamp", (0, 0, 120, 40), {"Name": "NotApproved"}

    )

    assert gen is not None

    assert b"1 0 0 RG" in gen.content  # default rubber-stamp red border

    assert b"(NOT APPROVED) Tj" in gen.content  # camel-split, upper-cased

    assert "Helv" in gen.fonts