# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_079.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_parser_rejects_non_digit_characters_and_reports_position() -> None:

    """Non-digit characters must be caught and the 1-based position must appear in the message."""

    with pytest.raises(InvalidInputError, match="position 4"):

        Ean13InputParser().parse("400A38133393")