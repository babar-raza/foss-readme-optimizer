# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_097.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean8_parser_rejects_bytes_input() -> None:

    """Bytes input is unsupported for EAN-8."""

    with pytest.raises(UnsupportedCapabilityError, match="bytes"):

        Ean8InputParser().parse(b"5512345")  # type: ignore[arg-type]
