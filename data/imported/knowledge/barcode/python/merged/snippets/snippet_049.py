# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_049.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_encoder_renders_display_text() -> None:

    """Display text should exclude sentinels/check char and escape control characters."""

    code_39_vector = next(

        vector for vector in CODE39_BASE_GOLDEN_VECTORS if vector.input_data == "CODE 39" and vector.add_check_digit

    )

    ht_vector = next(vector for vector in CODE39EXT_GOLDEN_VECTORS if vector.input_data == chr(9))

    del_vector = next(vector for vector in CODE39EXT_GOLDEN_VECTORS if vector.input_data == chr(127))



    code_39_symbol = Code39Encoder().encode(_build_payload(code_39_vector))

    ht_symbol = Code39Encoder().encode(_build_payload(ht_vector))

    del_symbol = Code39Encoder().encode(_build_payload(del_vector))



    assert code_39_symbol.metadata.display_text == "CODE 39"

    assert ht_symbol.metadata.display_text == "<HT>"

    assert del_symbol.metadata.display_text == "<DEL>"