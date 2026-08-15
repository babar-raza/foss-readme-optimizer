# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_012.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_default_utf8():

    result = detect_encoding(b"<p>Hello, world!</p>")

    assert result.encoding == "utf-8"

    assert result.confidence == "irrelevant"