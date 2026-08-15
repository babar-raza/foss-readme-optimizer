# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_088.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean8_row0_matches_golden_module_string(vector: Ean8Vector) -> None:

    symbol = Ean8Encoder().encode(_build_payload(vector.input_data))

    actual_row0 = "".join(str(bit) for bit in symbol.matrix.modules[0])

    assert actual_row0 == vector.expected_row0