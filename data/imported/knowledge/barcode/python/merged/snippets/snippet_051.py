# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_051.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_accepts_every_base_sub_group() -> None:

    """A digit, an uppercase letter and the base symbols should all be accepted in base mode."""

    data = "Z-. $/+%"



    payload = _base_parser().parse(data)



    assert payload.code39_encode_mode is Code39EncodeMode.BASE

    assert payload.data == data