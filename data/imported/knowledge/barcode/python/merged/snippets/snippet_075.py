# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_075.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_parser_rejects_bytes_input() -> None:

    """EAN-13 is a digit-only symbology and must not silently coerce bytes."""

    with pytest.raises(UnsupportedCapabilityError, match="bytes"):

        Ean13InputParser().parse(b"400638133393")  # type: ignore[arg-type]
