# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_068.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_row_heights_match_iso_constants(vector: Ean13Vector) -> None:

    """Row heights must match the ISO 15420 dimensional constants."""

    symbol = Ean13Encoder().encode(_build_payload(vector.input_data))



    assert symbol.matrix.row_heights_x == pytest.approx((EAN_BAR_HEIGHT_X, EAN_GUARD_EXTENSION_X))