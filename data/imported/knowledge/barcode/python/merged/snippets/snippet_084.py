# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_084.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_parser_rejects_13_digit_input_without_flag() -> None:

    """13-digit input is rejected by default; the message must name the enabling flag."""

    with pytest.raises(InvalidInputError, match="allow_check_digit_input"):

        Ean13InputParser().parse("4006381333931")