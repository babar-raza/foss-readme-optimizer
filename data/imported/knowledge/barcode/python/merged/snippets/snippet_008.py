# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_008.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_barcode_service_wraps_parser_not_implemented_errors() -> None:

    """Placeholder parser failures should surface as UnsupportedFeatureError."""

    events: list[str] = []

    parser = RecordingParser(

        payload=_build_payload(),

        events=events,

        failure=NotImplementedError("parse not implemented"),

    )

    service, _, encoder, _, _ = _build_service(parser=parser)



    with pytest.raises(UnsupportedFeatureError) as exc_info:

        service.generate(" CODE-128 ", "ABC123")



    assert "code128" in str(exc_info.value)

    assert "parse" in str(exc_info.value)

    assert events == ["parse"]

    assert encoder.calls == []