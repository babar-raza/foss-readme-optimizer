# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_027.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_unsupported_encoding_raises():

    with pytest.raises(UnsupportedEncodingError):

        decode_bytes(b"hello", "iso-2022-jp")