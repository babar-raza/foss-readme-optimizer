# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_093.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean8_parser_computes_check_digit_from_7_digit_input() -> None:

    """A 7-digit value gets its check digit computed and appended."""

    payload = Ean8InputParser().parse("5512345")

    assert payload == NormalizedPayload(symbology="ean8", data="55123457", input_kind="text")