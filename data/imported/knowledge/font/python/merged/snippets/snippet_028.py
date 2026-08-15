# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_028.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_notdef_glyph_cff(opensans_cff):

    glyph = opensans_cff.glyph_accessor.get_glyph_by_id(GlyphId(0))

    assert glyph.glyph_id == GlyphId(0)