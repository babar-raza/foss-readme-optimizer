# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_020.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_crlf_normalised():

    data = "line1\r\nline2\r\nline3".encode("utf-8")

    result = detect_encoding(data)

    assert "\r" not in result.text

    assert result.text == "line1\nline2\nline3"