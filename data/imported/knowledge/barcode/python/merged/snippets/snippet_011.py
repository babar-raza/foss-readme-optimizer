# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_011.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_generate_returns_a_public_code128_barcode() -> None:

    """The generic public entrypoint should return a real Code 128 barcode."""

    barcode_obj = barcode.generate("code128", "A")



    assert isinstance(barcode_obj, barcode.Barcode)

    assert barcode_obj.profile.name == "code128"

    assert barcode_obj.symbol.metadata.display_text == "A"