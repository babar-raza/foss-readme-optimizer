# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_064.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_save_pdf_with_pdfsaveoptions(self) -> None:

        from aspose.note import Document

        from aspose.note.saving import PdfSaveOptions



        doc = Document(self.path)

        buf = io.BytesIO()

        doc.Save(buf, PdfSaveOptions())

        self.assertTrue(buf.getvalue().startswith(b"%PDF"))