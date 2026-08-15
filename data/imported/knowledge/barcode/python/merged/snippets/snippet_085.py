# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_085.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_parser_rejects_wrong_check_digit_when_flag_is_set() -> None:

    """A 13-digit string with an incorrect check digit must fail even with the flag enabled."""

    with pytest.raises(InvalidInputError, match="mismatch"):

        Ean13InputParser().parse(

            "4006381333939",

            options=Ean13Options(allow_check_digit_input=True),

        )