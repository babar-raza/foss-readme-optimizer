# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_081.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_parser_rejects_non_ascii_digits() -> None:

    """Unicode decimal digits are not valid EAN-13 input characters."""

    with pytest.raises(InvalidInputError, match="position 12"):

        Ean13InputParser().parse("40063813339\u0663")