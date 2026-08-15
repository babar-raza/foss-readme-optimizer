# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_054.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_option_override_disables_full_ascii_on_ext_definition() -> None:

    """An explicit full_ascii=False should flip a Full-ASCII definition into base mode."""

    payload = _ext_parser().parse("ABC", options=Code39Options(full_ascii=False))



    assert payload.code39_encode_mode is Code39EncodeMode.BASE