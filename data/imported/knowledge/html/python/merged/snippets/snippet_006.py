# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_006.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_prescan_meta_charset_single_quote():

    assert prescan_meta_charset(b"<meta charset='utf-8'>") == "utf-8"