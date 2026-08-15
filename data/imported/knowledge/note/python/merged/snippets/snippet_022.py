# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_022.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_page_clone_duplicates_content_tree(self) -> None:

        from aspose.note import Document, Page, RichText



        page = Document(self.path).GetChildNodes(Page)[0]

        cloned = page.Clone()



        self.assertIsNot(cloned, page)

        self.assertEqual(len(list(cloned)), len(list(page)))

        self.assertEqual(len(cloned.GetChildNodes(RichText)), len(page.GetChildNodes(RichText)))

        self.assertIsNone(cloned.ParentNode)