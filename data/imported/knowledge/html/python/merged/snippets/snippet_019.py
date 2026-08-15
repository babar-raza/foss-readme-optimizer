# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_019.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_decode_shift_jis():

    original = "テスト"

    sjis_bytes = original.encode("shift_jis")

    text, errors = decode_bytes(sjis_bytes, "shift_jis")

    assert text == original

    assert errors == []