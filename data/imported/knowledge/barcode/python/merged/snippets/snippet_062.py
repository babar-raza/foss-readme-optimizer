# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_062.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_rejects_non_ascii_in_full_ascii_mode() -> None:

    """Full-ASCII mode should reject code points above 127."""

    with pytest.raises(InvalidInputError, match="position 1"):

        _ext_parser().parse("é")