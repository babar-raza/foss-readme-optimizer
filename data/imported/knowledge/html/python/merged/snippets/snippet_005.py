# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_005.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_prescan_meta_charset_double_quote():

    assert prescan_meta_charset(b'<meta charset="windows-1252">') == "windows-1252"