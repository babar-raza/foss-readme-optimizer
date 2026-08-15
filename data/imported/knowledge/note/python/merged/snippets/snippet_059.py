# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_059.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_root_namespace_does_not_export_save_options(self) -> None:

        import aspose.note



        self.assertFalse(hasattr(aspose.note, "SaveOptions"))

        self.assertFalse(hasattr(aspose.note, "PdfSaveOptions"))