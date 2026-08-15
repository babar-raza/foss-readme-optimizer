# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_006.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_animation_builder_supports_easing_and_coordinate_captions(testdata_dir) -> None:

    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"

    font = FontLoader.open(str(font_path))



    asset = AnimationPreviewBuilder.build_path(

        font,

        [

            AnimationStep({"wght": 400.0, "wdth": 100.0}, label="Regular"),

            AnimationStep({"wght": 700.0, "wdth": 75.0}, label="Condensed Bold"),

        ],

        text="A",

        frames_per_segment=3,

        preset="draft",

        easing="ease-in-out",

        caption_mode="both",

    )



    assert asset.frame_count == 3

    assert asset.frame_labels[0] == "Regular | wdth=100, wght=400"

    assert asset.frame_labels[-1] == "Condensed Bold | wdth=75, wght=700"