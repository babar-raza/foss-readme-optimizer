# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_063.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_accepts_star_in_full_ascii_mode() -> None:

    """The '*' character is only forbidden in base mode; Full-ASCII should accept it."""

    payload = _ext_parser().parse("*")



    assert payload.code39_encode_mode is Code39EncodeMode.FULL_ASCII

    assert payload.data == "*"