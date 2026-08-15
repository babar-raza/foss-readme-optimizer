# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_072.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_parser_accepts_second_known_12_digit_value() -> None:

    """A second known barcode verifies that check digit computation is not hard-coded."""

    payload = Ean13InputParser().parse("590123412345")



    assert payload == NormalizedPayload(symbology="ean13", data="5901234123457", input_kind="text")