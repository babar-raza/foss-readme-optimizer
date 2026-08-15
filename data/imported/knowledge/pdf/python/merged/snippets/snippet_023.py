# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_023.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_agl_named_glyphs() -> None:

    assert glyph_name_to_unicode("aacute") == "á"

    assert glyph_name_to_unicode("Euro") == "€"

    assert glyph_name_to_unicode("afii10017") == "А"  # Cyrillic A

    assert glyph_name_to_unicode("bullet") == "•"

    assert glyph_name_to_unicode("Lcommaaccent") == "Ļ"