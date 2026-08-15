# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_023.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_builtin_standard_encoding_uses_standard_table():

    charset = CffCharset([".notdef", "A", "space", "germandbls"])

    enc = CffEncoding.standard(charset)

    assert int(enc.unicode_to_gid(65)) == 1

    assert int(enc.unicode_to_gid(32)) == 2

    assert int(enc.unicode_to_gid(249)) == 3