# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_061.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_save_format_exports_only_pdf(self) -> None:

        from aspose.note import SaveFormat



        self.assertEqual(list(SaveFormat), [SaveFormat.Pdf])