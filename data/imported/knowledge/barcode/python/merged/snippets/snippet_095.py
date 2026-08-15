# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_095.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean8_parser_accepts_8_digit_input_when_flag_is_set() -> None:

    """An 8-digit value with a valid check digit is accepted when the flag is set."""

    payload = Ean8InputParser().parse("55123457", options=Ean8Options(allow_check_digit_input=True))

    assert payload == NormalizedPayload(symbology="ean8", data="55123457", input_kind="text")