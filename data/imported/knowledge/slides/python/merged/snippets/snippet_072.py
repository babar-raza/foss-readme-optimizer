# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_072.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_themed_background(tmp_pptx):

    """Themed background type and style_index round-trip."""

    pres = Presentation()

    slide = pres.slides[0]

    slide.background.type = BackgroundType.THEMED

    slide.background.style_index = 3



    pres2 = tmp_pptx(pres)

    bg = pres2.slides[0].background

    assert bg.type == BackgroundType.THEMED

    assert bg.style_index == 3

    pres2.dispose()