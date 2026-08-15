# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_036.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_encoder_rejects_code_a_lowercase() -> None:

    """CODE_A mode with a lowercase character (Code Set B-only) should raise InvalidInputError."""

    with pytest.raises(InvalidInputError):

        Code128Encoder().encode(_build_payload("a", encode_mode=Code128EncodeMode.CODE_A))