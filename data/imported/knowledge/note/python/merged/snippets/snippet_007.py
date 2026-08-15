# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_007.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_images_are_identical_by_hash(self) -> None:

        from aspose.note import Document, Image



        doc = Document(self.path)

        images = doc.GetChildNodes(Image)

        self.assertEqual(len(images), 3)



        digests = [hashlib.sha256(bytes(img.Bytes)).digest() for img in images]

        self.assertEqual(len(set(digests)), 1)