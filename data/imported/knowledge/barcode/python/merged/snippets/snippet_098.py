# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_098.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean8_parser_rejects_non_string_input() -> None:

    """Non-string, non-bytes input is rejected as invalid."""

    with pytest.raises(InvalidInputError, match="text string"):

        Ean8InputParser().parse(5512345)  # type: ignore[arg-type]
