# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_078.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_save_non_pdf_path_raises(self) -> None:

        from aspose.note import Document, UnsupportedSaveFormatException



        doc = Document(self.path)

        with self.assertRaises(UnsupportedSaveFormatException):

            doc.Save("unsupported-output.one")