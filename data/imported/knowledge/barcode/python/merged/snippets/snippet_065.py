# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_065.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_rejects_unsupported_option_containers(options: object) -> None:

    """Only the documented option container types should be accepted."""

    with pytest.raises(InvalidInputError, match="encode options"):

        _base_parser().parse("ABC", options=options)  # type: ignore[arg-type]
