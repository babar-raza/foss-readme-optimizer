# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_024.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_builtin_expert_encoding_uses_expert_table():

    charset = CffCharset([".notdef", "oneoldstyle", "Thornsmall"])

    enc = CffEncoding.expert(charset)

    assert int(enc.unicode_to_gid(49)) == 1

    assert int(enc.unicode_to_gid(251)) == 2