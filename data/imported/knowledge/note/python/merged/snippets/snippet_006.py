# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_006.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_images_exposed_and_have_bytes(self) -> None:

        from aspose.note import Document, Image



        doc = Document(self.path)

        images = doc.GetChildNodes(Image)

        self.assertEqual(len(images), 3)

        self.assertTrue(all(isinstance(img.Bytes, (bytes, bytearray)) for img in images))

        self.assertTrue(all(len(img.Bytes) > 1024 for img in images))