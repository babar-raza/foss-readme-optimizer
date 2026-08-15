# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_077.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_parser_rejects_empty_string() -> None:

    """An empty (or whitespace-only) string must not reach digit validation."""

    with pytest.raises(InvalidInputError, match="empty"):

        Ean13InputParser().parse("")