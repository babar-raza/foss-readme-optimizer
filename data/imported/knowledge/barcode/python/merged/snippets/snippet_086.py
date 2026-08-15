# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_086.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_parser_rejects_unsupported_capabilities(

    options: Ean13Options | EncodeOptions,

    message_fragment: str,

) -> None:

    """Requesting unsupported capabilities should raise a typed capability error."""

    with pytest.raises(UnsupportedCapabilityError, match=message_fragment):

        Ean13InputParser().parse("400638133393", options=options)