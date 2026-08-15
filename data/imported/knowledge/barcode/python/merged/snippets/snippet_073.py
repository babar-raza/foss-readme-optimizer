# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_073.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_parser_accepts_13_digit_input_when_flag_is_set() -> None:

    """13-digit input with a correct check digit should succeed when the flag is enabled."""

    payload = Ean13InputParser().parse(

        "4006381333931",

        options=Ean13Options(allow_check_digit_input=True),

    )



    assert payload == NormalizedPayload(symbology="ean13", data="4006381333931", input_kind="text")