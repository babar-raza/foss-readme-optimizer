# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_017.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_decode_windows1252_non_ascii():

    text, errors = decode_bytes(b"caf\xe9", "windows-1252")

    assert text == "caf\u00e9"

    assert errors == []