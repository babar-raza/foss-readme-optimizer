# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_026.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_encoder_supports_code_set_b_compatible_modes(

    mode: Code128EncodeMode,

) -> None:

    """CODE_B-compatible modes should encode 'A' with the same START_B plan."""

    payload = _build_payload(CODE128_A.input_data, encode_mode=mode)



    symbol = Code128Encoder().encode(payload)

    actual_rows = tuple("".join(str(module) for module in row) for row in symbol.matrix.modules)



    assert actual_rows == CODE128_A.expected_modules