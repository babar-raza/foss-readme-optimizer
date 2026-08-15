# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_026.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_agl_unresolved_and_bad_input() -> None:

    assert glyph_name_to_unicode(".notdef") is None

    assert glyph_name_to_unicode("nonexistentglyphname") is None

    assert glyph_name_to_unicode("") is None

    assert glyph_name_to_unicode("x" * 200) is None  # bounded name length

    assert glyph_name_to_unicode("uniD800") is None  # surrogate rejected
