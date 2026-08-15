# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_004.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_bom_overrides_prescan():

    # UTF-8 BOM present AND a windows-1252 meta charset in first 1024 bytes.

    body = b'<meta charset="windows-1252"><p>hi</p>'

    data = b"\xef\xbb\xbf" + body

    result = detect_encoding(data)

    # BOM must win.

    assert result.encoding == "utf-8"

    assert result.confidence == "certain"