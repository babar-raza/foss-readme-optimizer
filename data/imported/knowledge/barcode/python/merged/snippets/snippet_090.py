# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_090.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean8_row_heights_match_iso_constants(vector: Ean8Vector) -> None:

    symbol = Ean8Encoder().encode(_build_payload(vector.input_data))

    assert symbol.matrix.row_heights_x == pytest.approx((EAN8_BAR_HEIGHT_X, EAN_GUARD_EXTENSION_X))