# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_004.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_open_and_save_pdf_to_stream(self) -> None:

        from aspose.note import Document, SaveFormat



        doc = Document(self.path)

        self.assertFalse(hasattr(doc, "Count"))

        self.assertGreater(len(list(doc)), 0)



        buf = io.BytesIO()

        doc.Save(buf, SaveFormat.Pdf)

        data = buf.getvalue()

        self.assertTrue(data.startswith(b"%PDF"))

        self.assertGreater(len(data), 100)