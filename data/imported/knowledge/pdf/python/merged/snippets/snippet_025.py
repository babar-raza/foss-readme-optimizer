# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_025.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_agl_algorithmic_uni_forms() -> None:

    assert glyph_name_to_unicode("uni0041") == "A"

    assert glyph_name_to_unicode("uni00410042") == "AB"

    assert glyph_name_to_unicode("u1F600") == "\U0001f600"