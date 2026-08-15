# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_003.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_main_sequence_not_none(self):

        with Presentation() as pres:

            seq = pres.slides[0].timeline.main_sequence

            assert seq is not None