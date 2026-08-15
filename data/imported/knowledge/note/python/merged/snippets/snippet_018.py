# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_018.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_document_file_format_enum(self) -> None:

        from aspose.note import Document, FileFormat



        doc = Document(self.path)

        self.assertIsInstance(doc.FileFormat, FileFormat)