# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_042.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_clean_for_web_rejects_non_sfnt_fonts(opensans_cff_path: Path):

    font = FontLoader.open(str(opensans_cff_path))



    with pytest.raises(FontNotSupportedException):

        FontCleaner.clean_for_web(font)