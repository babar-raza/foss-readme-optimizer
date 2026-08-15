# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_080.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_parser_rejects_non_digit_characters_at_first_position() -> None:

    """A non-digit at position 1 should be reported correctly."""

    with pytest.raises(InvalidInputError, match="position 1"):

        Ean13InputParser().parse("X00638133393")