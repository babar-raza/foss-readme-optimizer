# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_031.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_parent_node_is_read_only_to_callers(self) -> None:

        from aspose.note import Document, Page



        doc = Document()

        page = Page()

        doc.AppendChildLast(page)



        self.assertIs(page.ParentNode, doc)



        with self.assertRaises(AttributeError):

            setattr(page, "ParentNode", None)