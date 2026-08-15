# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_030.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_encoder_rejects_code_c_non_digit_input() -> None:

    """CODE_C mode with non-digit input should raise InvalidInputError from the parser."""

    payload = _build_payload("A", encode_mode=Code128EncodeMode.CODE_C)

    with pytest.raises(InvalidInputError):

        Code128Encoder().encode(payload)