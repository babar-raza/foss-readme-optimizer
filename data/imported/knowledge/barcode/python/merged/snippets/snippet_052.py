# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_052.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_uses_definition_full_ascii_default() -> None:

    """The code39ext definition should default lowercase input to Full-ASCII mode."""

    payload = _ext_parser().parse("abc")



    assert payload.symbology == "code39ext"

    assert payload.code39_encode_mode is Code39EncodeMode.FULL_ASCII