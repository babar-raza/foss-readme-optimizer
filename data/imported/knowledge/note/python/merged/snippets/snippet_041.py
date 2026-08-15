# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_041.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_simple_table_published_history_matches_ui_structure(self) -> None:

        from aspose.note import Document, LoadOptions, Page



        fixture_path = _fixture_path("SimpleTable.one")

        if fixture_path is None:

            raise unittest.SkipTest("SimpleTable.one not found")



        doc = Document(fixture_path, LoadOptions(LoadHistory=True))

        current_page = doc.GetChildNodes(Page)[0]

        history = doc.GetPageHistory(current_page)



        self.assertEqual(len(history), 2)

        self.assertEqual(history.Current, current_page)

        self.assertEqual(

            _table_grid(current_page),

            [["1", "2", "3"], ["6", "5", "4"], ["7", "8", "9"], ["b", "a", "0"]],

        )



        previous_page = history[1]

        self.assertEqual(_page_body_text(previous_page), "fdf")

        self.assertEqual(_non_empty_outline_texts(previous_page), ["▪", "fdf"])



        oldest_page = history[0]

        self.assertEqual(_page_body_text(oldest_page), "")

        self.assertEqual(_non_empty_outline_texts(oldest_page), [])