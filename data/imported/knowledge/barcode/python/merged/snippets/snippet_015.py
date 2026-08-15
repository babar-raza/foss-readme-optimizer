# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_015.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_registry_returns_definitions_for_aliases() -> None:

    """Aliases should normalize to the same canonical definition."""

    registry = SymbologyRegistry()

    definition = _build_definition("code128", aliases=("code-128",))



    registry.register(definition)



    canonical = registry.get_definition("code128")

    alias = registry.get_definition(" CODE-128 ")



    assert alias is canonical

    assert alias.aliases == ("code-128",)