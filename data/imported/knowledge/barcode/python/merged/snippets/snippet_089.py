# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_089.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean8_matrix_dimensions(vector: Ean8Vector) -> None:

    symbol = Ean8Encoder().encode(_build_payload(vector.input_data))

    assert symbol.matrix.width == 67

    assert symbol.matrix.height == 2