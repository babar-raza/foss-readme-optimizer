# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_018.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_registry_rejects_duplicate_aliases() -> None:

    """Alias collisions should fail before mutating the registry."""

    registry = SymbologyRegistry()

    registry.register(_build_definition("code128", aliases=("code-128",)))



    with pytest.raises(ValueError, match="code-128"):

        registry.register(_build_definition("ean13", aliases=(" code-128 ",)))