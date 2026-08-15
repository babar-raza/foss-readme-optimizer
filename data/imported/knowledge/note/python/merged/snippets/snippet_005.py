# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_005.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_get_child_nodes_image(self) -> None:

        from aspose.note import Document, Image



        doc = Document(self.path)

        images = doc.GetChildNodes(Image)

        self.assertIsInstance(images, list)