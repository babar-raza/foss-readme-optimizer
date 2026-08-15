# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_004.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_main_sequence_initially_empty(self):

        with Presentation() as pres:

            assert pres.slides[0].timeline.main_sequence.count == 0