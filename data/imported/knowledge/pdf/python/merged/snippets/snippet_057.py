# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_057.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_line_converts_to_local_coordinates():

    # Rect origin (100,100); L is absolute -> local subtracts the origin.

    gen = build_appearance("Line", (100, 100, 300, 300), {"L": [120, 120, 220, 180]})

    assert gen is not None

    assert b"20 20 m" in gen.content

    assert b"120 80 l" in gen.content

    assert b"\nS\n" in gen.content