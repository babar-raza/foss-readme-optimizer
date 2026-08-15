# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_003.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_bom_utf16_be():

    payload = "<p>x</p>".encode("utf-16-be")

    data = b"\xfe\xff" + payload

    result = detect_encoding(data)

    assert result.encoding == "utf-16-be"

    assert result.confidence == "certain"