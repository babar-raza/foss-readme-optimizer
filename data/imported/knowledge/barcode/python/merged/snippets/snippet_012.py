# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_012.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_helper_returns_a_public_code128_barcode() -> None:

    """The dedicated helper should return the same public result shape."""

    barcode_obj = barcode.code128("A")



    assert isinstance(barcode_obj, barcode.Barcode)

    assert barcode_obj.profile.name == "code128"

    assert barcode_obj.symbol.metadata.display_text == "A"