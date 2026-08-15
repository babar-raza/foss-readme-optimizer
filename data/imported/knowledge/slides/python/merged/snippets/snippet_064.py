# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_064.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_solid_background_on_slide(tmp_pptx):

    """Solid-colour background on a normal slide round-trips."""

    pres = Presentation()

    slide = pres.slides[0]

    slide.background.type = BackgroundType.OWN_BACKGROUND

    slide.background.fill_format.fill_type = FillType.SOLID

    slide.background.fill_format.solid_fill_color.color = Color.blue



    pres2 = tmp_pptx(pres)

    bg = pres2.slides[0].background

    assert bg.type == BackgroundType.OWN_BACKGROUND

    assert bg.fill_format.fill_type == FillType.SOLID

    c = bg.fill_format.solid_fill_color.color

    assert c.r == 0 and c.g == 0 and c.b == 255

    pres2.dispose()