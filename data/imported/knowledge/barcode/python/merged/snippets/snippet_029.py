# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_029.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_encoder_rejects_reference_invalid_text_cases(

    input_data: str,

) -> None:

    """Non-Code-128 Unicode inputs from the fixture pack should fail predictably."""

    with pytest.raises(InvalidInputError, match="unsupported Code 128 character"):

        Code128Encoder().encode(_build_payload(input_data))