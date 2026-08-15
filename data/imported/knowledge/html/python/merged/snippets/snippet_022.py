# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_022.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_replacement_char_recorded():

    # 0x81 is undefined in cp1252 → produces U+FFFD with errors='replace'.

    text, errors = decode_bytes(b"\x81", "windows-1252")

    assert "\ufffd" in text

    assert any("decode-error" in e for e in errors)