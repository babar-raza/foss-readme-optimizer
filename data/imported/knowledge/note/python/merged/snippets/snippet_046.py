# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_046.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_richtext_runs_preserved(self) -> None:

        from aspose.note import Document, RichText



        doc = Document(self.path)

        rts = doc.GetChildNodes(RichText)

        self.assertGreater(len(rts), 0)



        # At least one RichText node should carry extracted formatting runs.

        self.assertTrue(any(len(rt.TextRuns) > 0 for rt in rts))