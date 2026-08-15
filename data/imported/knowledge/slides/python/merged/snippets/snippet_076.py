# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_076.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_effective_inherits_from_master():

    """Slide with NOT_DEFINED bg inherits from master."""

    pres = Presentation()

    master = pres.masters[0]

    master.background.type = BackgroundType.OWN_BACKGROUND

    master.background.fill_format.fill_type = FillType.SOLID

    master.background.fill_format.solid_fill_color.color = Color.dark_green



    slide = pres.slides[0]

    assert slide.background.type == BackgroundType.NOT_DEFINED



    eff = slide.background.get_effective()

    assert eff.fill_format.fill_type == FillType.SOLID

    c = eff.fill_format.solid_fill_color

    assert c.r == 0 and c.g == 100 and c.b == 0

    pres.dispose()