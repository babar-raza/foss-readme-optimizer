# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_021.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_richtext_supports_dotnet_text_runs_alias(self) -> None:

        from aspose.note import Document, RichText



        doc = Document(self.path)

        rich_text = next(rt for rt in doc.GetChildNodes(RichText) if rt.TextRuns)



        self.assertFalse(hasattr(rich_text, "Runs"))

        self.assertGreater(len(rich_text.TextRuns), 0)

        self.assertEqual(rich_text.Length, len(rich_text.Text))