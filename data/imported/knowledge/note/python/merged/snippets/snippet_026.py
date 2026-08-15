# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_026.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_single_page_fixtures_do_not_create_synthetic_titles(self) -> None:

        from aspose.note import Document, Page



        for fixture_name in ("SimpleTable.one", "3ImagesWithDifferentAlignment.one"):

            path = _fixture_path(fixture_name)

            if path is None:

                raise unittest.SkipTest(f"{fixture_name} not found")



            doc = Document(path)

            pages = doc.GetChildNodes(Page)



            self.assertEqual(len(pages), 1)

            self.assertIsNone(pages[0].Title, fixture_name)

            self.assertEqual(pages[0].Level, 1, fixture_name)