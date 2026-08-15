# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_060.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_pdf_save_options_roundtrip(self) -> None:

        from aspose.note import SaveFormat

        from aspose.note.saving import PdfSaveOptions



        opts = PdfSaveOptions()

        self.assertEqual(opts.SaveFormat, SaveFormat.Pdf)

        self.assertEqual(opts.PageIndex, 0)

        self.assertIsNone(opts.PageCount)

        self.assertFalse(hasattr(opts, "TagIconDir"))

        self.assertFalse(hasattr(opts, "TagIconSize"))

        self.assertFalse(hasattr(opts, "TagIconGap"))