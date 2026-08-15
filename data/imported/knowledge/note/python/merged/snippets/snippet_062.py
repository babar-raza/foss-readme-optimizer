# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_062.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_save_options_expose_common_base_properties(self) -> None:

        from aspose.note import SaveFormat

        from aspose.note.saving import PdfSaveOptions



        opts = PdfSaveOptions(PageIndex=2, PageCount=3, FontsSubsystem="fonts-subsystem")

        self.assertEqual(opts.SaveFormat, SaveFormat.Pdf)

        self.assertEqual(opts.PageIndex, 2)

        self.assertEqual(opts.PageCount, 3)

        self.assertEqual(opts.FontsSubsystem, "fonts-subsystem")