# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_036.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_page_history_constructor_accepts_only_current_page(self) -> None:

        from aspose.note import Page, PageHistory



        current = Page()

        history = PageHistory(current)



        self.assertIs(history.Current, current)



        with self.assertRaises(TypeError):

            PageHistory(current, [Page()])