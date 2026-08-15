# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_007.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_prescan_http_equiv():

    data = b'<meta http-equiv="Content-Type" content="text/html; charset=gbk">'

    assert prescan_meta_charset(data) == "gbk"