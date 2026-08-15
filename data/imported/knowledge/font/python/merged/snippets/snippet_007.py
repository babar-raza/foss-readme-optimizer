# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_007.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_animation_builder_named_instance_path_requires_two_steps(testdata_dir) -> None:

    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"

    font = FontLoader.open(str(font_path))



    with pytest.raises(ValueError, match="at least two steps"):

        AnimationPreviewBuilder.build_named_instance_path(font, ["Bold"])