# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_059.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_rejects_empty_text() -> None:

    """Code 39 requires at least one supported text character."""

    with pytest.raises(InvalidInputError, match="empty"):

        _base_parser().parse("")