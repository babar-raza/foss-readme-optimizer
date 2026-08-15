# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_074.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_parser_accepts_encode_options_base_type() -> None:

    """EncodeOptions (base type) should be accepted and coerced to Ean13Options defaults."""

    payload = Ean13InputParser().parse("400638133393", options=EncodeOptions())



    assert payload.data == "4006381333931"