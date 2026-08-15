# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_056.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_defaults_check_digit_to_false() -> None:

    """Without an explicit request the payload should report no check digit."""

    payload = _base_parser().parse("ABC")



    assert payload.code39_add_check_digit is False