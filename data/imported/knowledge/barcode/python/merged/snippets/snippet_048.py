# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_048.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_encoder_matches_golden_modules(vector: Code39Vector) -> None:

    """Code 39 encoding should match a known-good module sequence."""

    symbol = Code39Encoder().encode(_build_payload(vector))

    actual_rows = tuple("".join(str(module) for module in row) for row in symbol.matrix.modules)



    assert actual_rows == vector.expected_modules

    assert symbol.matrix.height == 1