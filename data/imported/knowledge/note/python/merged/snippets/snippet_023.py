# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_023.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_page_clone_accepts_clone_history_keyword(self) -> None:

        from aspose.note import Document, Page



        page = Document(self.path).GetChildNodes(Page)[0]

        cloned = page.Clone(cloneHistory=True)



        self.assertIsNot(cloned, page)