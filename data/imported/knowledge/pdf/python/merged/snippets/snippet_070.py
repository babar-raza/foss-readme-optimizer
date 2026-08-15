# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_070.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_caret_draws_filled_triangle():

    gen = build_appearance("Caret", (0, 0, 20, 20), {})

    assert gen is not None

    assert b"0 g" in gen.content  # defaults to black

    assert gen.content.count(b" l\n") == 2  # two edges of the triangle

    assert b"\nh\n" in gen.content and b"\nf\n" in gen.content

    assert gen.fonts == {}  # marker shape needs no font
