# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_032.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_encoder_matches_code_set_a_golden_vectors(

    vector: Code128Vector,

) -> None:

    """Code Set A encoding should match BWIPP golden fixtures and escape-render control chars."""

    encoder = Code128Encoder()

    symbol = encoder.encode(_build_payload(vector.input_data, encode_mode=Code128EncodeMode.CODE_A))

    actual_rows = tuple("".join(str(m) for m in row) for row in symbol.matrix.modules)



    assert actual_rows == vector.expected_modules

    assert "\x00" not in symbol.metadata.display_text

    assert "<" in symbol.metadata.display_text