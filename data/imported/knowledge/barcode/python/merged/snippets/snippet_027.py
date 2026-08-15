# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_027.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_encoder_rejects_invalid_payload_contract(

    payload: NormalizedPayload,

) -> None:

    """Encoder contract violations should raise invalid-input errors."""

    with pytest.raises(InvalidInputError):

        Code128Encoder().encode(payload)