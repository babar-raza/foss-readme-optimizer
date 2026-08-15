# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_031.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_encoder_matches_code_set_c_golden_vectors(

    vector: Code128Vector,

) -> None:

    """Code Set C encoding should match BWIPP golden fixtures."""

    actual = _render_modules(vector, encode_mode=Code128EncodeMode.CODE_C)

    assert actual == vector.expected_modules