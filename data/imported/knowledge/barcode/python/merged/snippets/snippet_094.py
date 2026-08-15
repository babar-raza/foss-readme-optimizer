# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_094.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean8_parser_computes_check_digit_for_second_value() -> None:

    """A second 7-digit value confirms the check digit is computed, not hard-coded."""

    payload = Ean8InputParser().parse("1234567")

    assert payload.data == "12345670"