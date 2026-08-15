# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_084.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_imports_smoke(self) -> None:

        import aspose.note

        import aspose.note.saving  # noqa: F401

        from aspose.note import Document, Outline, Page, ParagraphStyle, RichText  # noqa: F401

        from aspose.note.saving import PdfSaveOptions, SaveOptions  # noqa: F401



        self.assertFalse(hasattr(aspose.note, "SaveOptions"))

        self.assertFalse(hasattr(aspose.note, "PdfSaveOptions"))