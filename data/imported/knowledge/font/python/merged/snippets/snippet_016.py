# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_016.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_otf_embedded_cff_available(opensans_cff_path: Path):

    otf_data = _wrap_otf_with_cff(opensans_cff_path.read_bytes())

    font = FontLoader.open(otf_data)

    assert isinstance(font, TtfFont)

    assert font.cff_font is not None

    assert isinstance(font.cff_font, CffFont)