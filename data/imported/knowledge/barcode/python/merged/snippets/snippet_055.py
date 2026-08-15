# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_055.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_carries_check_digit_request() -> None:

    """A check-digit request should propagate onto the normalized payload."""

    payload = _base_parser().parse("ABC", options=Code39Options(add_check_digit=True))



    assert payload.code39_add_check_digit is True