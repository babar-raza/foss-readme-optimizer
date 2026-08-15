# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_042.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_parser_rejects_unsupported_capabilities(

    options: Code128Options | EncodeOptions,

    message_fragment: str,

) -> None:

    """Unsupported capabilities should fail as typed capability errors."""

    with pytest.raises(UnsupportedCapabilityError, match=message_fragment):

        Code128InputParser().parse("ABC123", options=options)