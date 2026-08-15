# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_024.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_encoder_reference_behavior_vectors(

    vector: Code128Vector,

) -> None:

    """AUTO-mode reference fixtures should match their known-good module sequence."""

    assert _render_modules(vector, encode_mode=Code128EncodeMode.AUTO) == vector.expected_modules