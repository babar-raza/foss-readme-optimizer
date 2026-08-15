# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_092.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean8_metadata_fields(vector: Ean8Vector) -> None:

    symbol = Ean8Encoder().encode(_build_payload(vector.input_data))

    assert symbol.metadata.symbology == "ean8"

    assert symbol.metadata.input_kind == "text"

    assert symbol.metadata.normalized_data == vector.input_data

    assert symbol.metadata.display_text == vector.input_data