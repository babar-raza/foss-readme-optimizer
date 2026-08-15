# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_067.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_matrix_dimensions(vector: Ean13Vector) -> None:

    """EAN-13 matrix must be exactly 95 modules wide and 2 rows tall."""

    symbol = Ean13Encoder().encode(_build_payload(vector.input_data))



    assert symbol.matrix.width == 95

    assert symbol.matrix.height == 2