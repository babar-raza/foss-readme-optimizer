# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_003.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_barcode_service_rejects_blank_and_non_string_symbologies(

    symbology: object,

) -> None:

    """Invalid public symbology selectors should fail before registry lookup."""

    service = BarcodeService(

        registry=SymbologyRegistry(),

        options_resolver=OptionsResolver(),

    )



    with pytest.raises(InvalidInputError, match="symbology"):

        service.generate(symbology, "ABC123")