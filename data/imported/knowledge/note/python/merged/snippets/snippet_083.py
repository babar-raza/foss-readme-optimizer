# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_083.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_attachment_with_tag_fixture_has_tags_somewhere(self) -> None:

        p = _fixture_path("AttachedFileWithTag.one")

        if p is None:

            raise unittest.SkipTest("AttachedFileWithTag.one not found")



        from aspose.note import AttachedFile, Document



        doc = Document(p)

        atts = doc.GetChildNodes(AttachedFile)

        self.assertGreaterEqual(len(atts), 1)



        # Strict: this fixture is expected to include note tags.

        tags = _collect_all_tags(doc)

        self.assertGreaterEqual(len(tags), 1)

        self.assertTrue(any(_tag_is_meaningful(t) for t in tags))