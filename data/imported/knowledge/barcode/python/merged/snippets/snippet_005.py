# Adapted from aspose.org: knowledge/barcode/python/merged/snippets/snippet_005.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_barcode_service_returns_barcode_with_normalized_render_options() -> None:

    """Generation-time render overrides should be normalized and stored on the result."""

    service, _, encoder, profile, _ = _build_service()



    barcode = service.generate(

        "code128",

        "ABC123",

        render=RenderOptions(

            scale=2.5,

            foreground_color=" #222222 ",

            font_family=" IBM Plex Sans ",

        ),

    )



    assert barcode == Barcode(

        symbol=encoder.symbol,

        profile=profile,

        default_render_options=RenderOptions(

            scale=2.5,

            foreground_color="#222222",

            font_family="IBM Plex Sans",

        ),

    )