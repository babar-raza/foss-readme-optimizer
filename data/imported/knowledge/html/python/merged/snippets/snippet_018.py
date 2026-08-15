# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_018.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_decode_gbk():

    original = "你好"

    gbk_bytes = original.encode("gbk")

    text, errors = decode_bytes(gbk_bytes, "gbk")

    assert text == original

    assert errors == []