# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_029.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_glyph_path_has_curveto(opensans_cff):

    gid = opensans_cff.encoding.unicode_to_gid(0x41)

    glyph = opensans_cff.glyph_accessor.get_glyph_by_id(gid)

    assert glyph.path is not None

    cmds = _commands(glyph.path)

    assert any(isinstance(c, MoveTo) for c in cmds)

    assert any(isinstance(c, CurveTo) for c in cmds)