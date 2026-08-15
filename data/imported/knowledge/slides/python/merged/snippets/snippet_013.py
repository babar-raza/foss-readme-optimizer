# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_013.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_no_animation_slide_has_zero_effects(self, tmp_pptx):

        """A slide without animations should have an empty sequence on reload."""

        pres = Presentation()

        pres.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 10, 10, 50, 50)



        pres2 = tmp_pptx(pres)

        assert pres2.slides[0].timeline.main_sequence.count == 0

        pres2.dispose()