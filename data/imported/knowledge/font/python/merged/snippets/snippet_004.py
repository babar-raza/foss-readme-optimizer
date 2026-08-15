# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_004.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_animation_builder_exposes_presets() -> None:

    assert AnimationPreviewBuilder.available_presets() == ("draft", "standard", "showcase")