# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_045.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_parser_accepts_control_characters_in_auto_mode() -> None:

    """AUTO should preserve standard-valid Code Set A control characters."""

    payload = Code128InputParser().parse("A\n")



    assert payload == NormalizedPayload(

        symbology="code128",

        data="A\n",

        input_kind="text",

        code128_encode_mode=Code128EncodeMode.AUTO,

    )