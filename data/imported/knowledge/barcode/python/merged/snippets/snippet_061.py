# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_061.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_rejects_base_out_of_set_characters(data: str, position: int) -> None:

    """Characters outside the 43-character base set should fail with a 1-based position."""

    with pytest.raises(InvalidInputError, match=f"position {position}"):

        _base_parser().parse(data)