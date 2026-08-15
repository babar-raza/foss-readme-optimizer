# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_037.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_set_build_type(self):

        with Presentation() as pres:

            slide = pres.slides[0]

            shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 10, 10, 100, 50)

            effect = slide.timeline.main_sequence.add_effect(

                shape, anim.EffectType.FADE,

                anim.EffectSubtype.NONE,

                anim.EffectTriggerType.ON_CLICK,

            )

            effect.text_animation.build_type = anim.BuildType.BY_LEVEL_PARAGRAPHS1

            assert effect.text_animation.build_type == anim.BuildType.BY_LEVEL_PARAGRAPHS1