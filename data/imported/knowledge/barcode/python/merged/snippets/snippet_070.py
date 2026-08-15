# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_070.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ean13_metadata_fields(vector: Ean13Vector) -> None:

    """Symbol metadata must reflect the normalized 13-digit input and display text."""

    symbol = Ean13Encoder().encode(_build_payload(vector.input_data))



    assert symbol.metadata.symbology == "ean13"

    assert symbol.metadata.input_kind == "text"

    assert symbol.metadata.normalized_data == vector.input_data

    assert symbol.metadata.display_text == vector.input_data