# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_076.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_parser_rejects_non_string_input() -> None:

    """Only text strings are valid; other types must be rejected with a clear error."""

    with pytest.raises(InvalidInputError, match="text string"):

        Ean13InputParser().parse(400638133393)  # type: ignore[arg-type]
