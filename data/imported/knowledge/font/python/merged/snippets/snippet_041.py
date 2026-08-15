# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_041.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_clean_for_web_supports_wrapper_fonts(roboto_path: Path):

    font = _font_with_extra_metadata(roboto_path)

    wrapped = FontConverter.convert(font, FontType.WOFF)

    assert isinstance(wrapped, WoffFont)



    cleaned = FontCleaner.clean_for_web(wrapped)



    assert isinstance(cleaned, WoffFont)

    assert "DSIG" not in cleaned.inner_font.ttf_tables._raw

    assert "FFTM" not in cleaned.inner_font.ttf_tables._raw

    assert "meta" not in cleaned.inner_font.ttf_tables._raw

    assert cleaned.inner_font.ttf_tables.name is not None

    assert all(record.platform_id != 1 for record in cleaned.inner_font.ttf_tables.name.records)