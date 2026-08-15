# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_046.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_parser_rejects_non_enum_encode_modes(options: Code128Options) -> None:

    """encode_mode must be expressed through the shared Code128 enum."""

    with pytest.raises(InvalidInputError, match="Code128EncodeMode"):

        Code128InputParser().parse("ABC123", options=options)