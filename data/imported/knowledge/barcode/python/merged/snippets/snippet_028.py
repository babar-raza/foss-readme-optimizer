# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_028.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_encoder_rejects_unsupported_text_characters(input_data: str) -> None:

    """Unsupported characters should fail with the typed input error."""

    payload = _build_payload(input_data)



    with pytest.raises(InvalidInputError, match="character"):

        Code128Encoder().encode(payload)