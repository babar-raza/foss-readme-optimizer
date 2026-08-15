# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_083.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_parser_rejects_various_wrong_lengths(length: int) -> None:

    """Any digit-only string that is neither 12 nor 13 characters must be rejected."""

    data = "1" * length

    with pytest.raises(InvalidInputError, match="12 or 13 digits"):

        Ean13InputParser().parse(data)