# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_063.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_save_format_is_read_only(self) -> None:

        from aspose.note import SaveFormat

        from aspose.note.saving import PdfSaveOptions



        opts = PdfSaveOptions()



        with self.assertRaises(AttributeError):

            setattr(opts, "SaveFormat", SaveFormat.Pdf)