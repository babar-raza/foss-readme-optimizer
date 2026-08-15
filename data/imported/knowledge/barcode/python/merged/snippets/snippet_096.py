# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_096.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean8_parser_accepts_encode_options_base_type() -> None:

    """The base EncodeOptions type is accepted and coerced."""

    payload = Ean8InputParser().parse("5512345", options=EncodeOptions())

    assert payload.data == "55123457"