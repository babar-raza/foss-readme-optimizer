# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_064.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_preserves_whitespace_verbatim() -> None:

    """Supported spaces should survive parsing without trimming or rewriting."""

    data = "A B C"



    payload = _base_parser().parse(data)



    assert payload.data == data