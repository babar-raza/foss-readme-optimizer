# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_041.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_parser_preserves_supported_typed_encode_modes(

    data: str,

    mode: Code128EncodeMode,

) -> None:

    """Parser output should carry the exact typed encode mode through to encoding."""

    payload = Code128InputParser().parse(data, options=Code128Options(encode_mode=mode))



    assert payload.code128_encode_mode is mode