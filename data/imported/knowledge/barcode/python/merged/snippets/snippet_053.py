# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_053.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code39_parser_option_override_enables_full_ascii_on_base_definition() -> None:

    """An explicit full_ascii=True should flip a base definition into Full-ASCII mode."""

    payload = _base_parser().parse("abc", options=Code39Options(full_ascii=True))



    assert payload.code39_encode_mode is Code39EncodeMode.FULL_ASCII