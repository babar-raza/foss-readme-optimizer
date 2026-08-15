# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_014.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_registry_returns_definitions_for_canonical_names() -> None:

    """Canonical-name lookup should resolve the stored definition."""

    registry = SymbologyRegistry()

    definition = _build_definition("code128")



    registry.register(definition)



    resolved = registry.get_definition(" CODE128 ")



    assert resolved.name == "code128"

    assert resolved.aliases == ()

    assert registry.get_parser("code128") is resolved.parser

    assert registry.get_encoder("code128") is resolved.encoder

    assert registry.get_profile("code128") is resolved.profile