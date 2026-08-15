# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_055.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_square_without_colour_defaults_to_black_border():

    gen = build_appearance("Square", (0, 0, 50, 50), {})

    assert gen is not None

    assert b"0 G" in gen.content

    assert b"\nS\n" in gen.content  # stroke only
