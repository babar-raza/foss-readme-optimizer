# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_017.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_cff_truncated_raises(opensans_cff_path: Path):

    payload = _extract_embedded_cff(opensans_cff_path.read_bytes())

    with pytest.raises(FontParseException):

        FontLoader.open(payload[:40], font_type=FontType.CFF)