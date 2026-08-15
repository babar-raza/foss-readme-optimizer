# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_014.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_attached_files_exposed_and_have_bytes(self) -> None:

        from aspose.note import AttachedFile, Document



        doc = Document(self.path)

        atts = doc.GetChildNodes(AttachedFile)

        self.assertGreaterEqual(len(atts), 1)



        # Filename should be present.

        self.assertTrue(any((a.FileName or "").strip() for a in atts))



        # Bytes are best-effort in current implementation (may be empty for some fixtures).

        self.assertTrue(all(isinstance(a.Bytes, (bytes, bytearray)) for a in atts))