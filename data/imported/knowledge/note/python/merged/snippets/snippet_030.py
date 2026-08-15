# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_030.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_document_does_not_expose_non_dotnet_count_method(self) -> None:

        from aspose.note import Document, Page



        doc = Document()

        doc.AppendChildLast(Page())



        self.assertFalse(hasattr(doc, "Count"))

        self.assertEqual(len(list(doc)), 1)