# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_002.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_title_nodes_are_visible(self) -> None:

        from aspose.note import Document, Title



        doc = Document(self.path)

        titles = doc.GetChildNodes(Title)

        self.assertGreaterEqual(len(titles), 1)