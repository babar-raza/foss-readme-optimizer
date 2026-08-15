# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_021.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_default_service_bootstrap_wires_registry_and_options_resolver() -> None:

    """The default service bootstrap should wire a fresh registry and resolver."""

    service = build_default_service()



    assert isinstance(service, BarcodeService)

    assert isinstance(service.registry, SymbologyRegistry)

    assert isinstance(service.options_resolver, OptionsResolver)

    assert service.registry.get_definition("upce").name == "upce"