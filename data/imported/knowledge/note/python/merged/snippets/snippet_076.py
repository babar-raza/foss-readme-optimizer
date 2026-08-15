# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_076.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_pdf_writer_uses_base14_fonts_by_default(self) -> None:

        from aspose.note.saving.pdf_writer import _register_font_variant



        self.assertEqual(_register_font_variant("sans", False, False), "Helvetica")

        self.assertEqual(_register_font_variant("serif", False, True), "Times-Italic")