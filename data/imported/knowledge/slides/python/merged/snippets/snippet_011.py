# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_011.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_fade_persists(self, tmp_pptx):

        pres = Presentation()

        slide = pres.slides[0]

        shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 10, 10, 100, 50)

        slide.timeline.main_sequence.add_effect(

            shape, anim.EffectType.FADE,

            anim.EffectSubtype.NONE,

            anim.EffectTriggerType.ON_CLICK,

        )



        pres2 = tmp_pptx(pres)

        seq2 = pres2.slides[0].timeline.main_sequence

        assert seq2.count == 1

        assert seq2[0].type == anim.EffectType.FADE

        assert seq2[0].subtype == anim.EffectSubtype.NONE

        assert seq2[0].preset_class_type == anim.EffectPresetClassType.ENTRANCE

        pres2.dispose()