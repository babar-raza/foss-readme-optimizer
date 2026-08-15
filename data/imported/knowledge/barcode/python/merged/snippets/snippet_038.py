# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_038.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_code128_parser_accepts_supported_text_and_option_forms(

    data: str,

    options: Code128Options | EncodeOptions | None,

) -> None:

    """Supported text input should normalize into the Code 128 payload contract."""

    payload = Code128InputParser().parse(data, options=options)



    assert payload == NormalizedPayload(

        symbology="code128",

        data=data,

        input_kind="text",

        code128_encode_mode=Code128EncodeMode.AUTO,

    )