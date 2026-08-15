# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_016.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_registry_raises_for_unknown_names() -> None:

    """Unknown normalized names should raise SymbologyNotFoundError."""

    registry = SymbologyRegistry()



    with pytest.raises(SymbologyNotFoundError, match="missing"):

        registry.get_definition(" missing ")