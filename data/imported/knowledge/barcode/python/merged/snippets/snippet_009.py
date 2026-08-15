# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_009.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_barcode_service_wraps_encoder_not_implemented_errors() -> None:

    """Placeholder encoder failures should surface as UnsupportedFeatureError."""

    events: list[str] = []

    encoder = RecordingEncoder(

        symbol=_build_symbol(),

        events=events,

        failure=NotImplementedError("encode not implemented"),

    )

    service, parser, _, _, _ = _build_service(encoder=encoder)



    with pytest.raises(UnsupportedFeatureError) as exc_info:

        service.generate("code128", "ABC123")



    assert "code128" in str(exc_info.value)

    assert "encode" in str(exc_info.value)

    assert events == ["parse", "encode"]

    assert parser.calls == [("ABC123", None)]