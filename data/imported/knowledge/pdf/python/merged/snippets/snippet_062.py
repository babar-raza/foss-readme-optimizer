# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_062.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_underline_and_strikeout_draw_lines():

    quad = {"QuadPoints": [0, 20, 100, 20, 0, 0, 100, 0]}

    under = build_appearance("Underline", (0, 0, 100, 20), quad)

    strike = build_appearance("StrikeOut", (0, 0, 100, 20), quad)

    assert under is not None and strike is not None

    assert b"\nS\n" in under.content

    assert b"\nS\n" in strike.content

    # Strike-out sits higher than the underline.

    assert under.content != strike.content