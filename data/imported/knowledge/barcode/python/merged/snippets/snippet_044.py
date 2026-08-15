# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_044.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_parser_rejects_text_that_conflicts_with_the_requested_mode(

    data: str,

    options: Code128Options | None,

    message_fragment: str,

) -> None:

    """Standard-invalid text should fail before the encoder runs."""

    with pytest.raises(InvalidInputError, match=message_fragment):

        Code128InputParser().parse(data, options=options)