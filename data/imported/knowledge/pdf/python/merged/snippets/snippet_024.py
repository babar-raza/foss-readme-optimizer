# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_024.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_agl_ligature_and_variant_components() -> None:

    assert glyph_name_to_unicode("f_f_i") == "ffi"

    assert glyph_name_to_unicode("A.sc") == "A"

    assert glyph_name_to_unicode("fi") == "ﬁ"  # a real AGL ligature name
