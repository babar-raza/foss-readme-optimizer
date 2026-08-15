# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_005.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_interactive_sequences_initially_empty(self):

        with Presentation() as pres:

            assert len(pres.slides[0].timeline.interactive_sequences) == 0