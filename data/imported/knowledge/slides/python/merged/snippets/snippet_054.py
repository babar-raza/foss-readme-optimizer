# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_054.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_get_effects_by_paragraph_no_match(self):

        """Paragraphs without animation return empty list."""

        with Presentation() as pres:

            slide = pres.slides[0]

            shape, paras = self._make_shape_with_paragraphs(slide)

            seq = slide.timeline.main_sequence



            # Add shape-level animation (no paragraph targeting)

            seq.add_effect(shape, anim.EffectType.FADE,

                           anim.EffectSubtype.NONE,

                           anim.EffectTriggerType.ON_CLICK)



            # Shape-level effect should NOT match paragraph queries

            assert len(seq.get_effects_by_paragraph(paras[0])) == 0

            assert len(seq.get_effects_by_paragraph(paras[1])) == 0