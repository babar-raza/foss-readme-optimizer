# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_060.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_rejects_unsupported_capabilities(

    options: Code39Options,

    message_fragment: str,

) -> None:

    """GS1 and ECI requests should fail as typed capability errors."""

    with pytest.raises(UnsupportedCapabilityError, match=message_fragment):

        _base_parser().parse("ABC", options=options)