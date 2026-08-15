# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_033.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_getitem(self):

        with Presentation() as pres:

            slide = pres.slides[0]

            shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 10, 10, 100, 50)

            seq = slide.timeline.main_sequence

            seq.add_effect(shape, anim.EffectType.FADE, anim.EffectSubtype.NONE,

                           anim.EffectTriggerType.ON_CLICK)

            assert seq[0].type == anim.EffectType.FADE