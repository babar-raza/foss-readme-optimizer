# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_023.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_result_has_encoding_attr():

    result = detect_encoding(b"<p>hello</p>")

    assert isinstance(result.encoding, str)

    assert result.encoding