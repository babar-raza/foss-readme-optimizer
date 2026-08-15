# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_058.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_rejects_bytes_input() -> None:

    """Bytes input should fail as an unsupported capability rather than silently decode."""

    with pytest.raises(UnsupportedCapabilityError, match="bytes"):

        _base_parser().parse(b"ABC")