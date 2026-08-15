# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_017.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_timing_persists(self, tmp_pptx):

        pres = Presentation()

        slide = pres.slides[0]

        shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 10, 10, 100, 50)

        effect = slide.timeline.main_sequence.add_effect(

            shape, anim.EffectType.FADE,

            anim.EffectSubtype.NONE,

            anim.EffectTriggerType.ON_CLICK,

        )

        effect.timing.duration = 2.5

        effect.timing.trigger_delay_time = 0.5



        pres2 = tmp_pptx(pres)

        eff2 = pres2.slides[0].timeline.main_sequence[0]

        assert eff2.timing.duration == 2.5

        assert eff2.timing.trigger_delay_time == 0.5

        pres2.dispose()