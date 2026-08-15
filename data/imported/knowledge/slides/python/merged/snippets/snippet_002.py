# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_002.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_timeline_not_none(self):

        with Presentation() as pres:

            tl = pres.slides[0].timeline

            assert tl is not None