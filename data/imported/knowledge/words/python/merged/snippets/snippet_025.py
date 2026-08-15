# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_025.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_save_with_pdf_save_options(self):

        """PdfSaveOptions is accepted for API compatibility."""

        # ExStart:SaveWithPdfSaveOptions

        save_options = aw.saving.PdfSaveOptions()

        self.convert(

            "test_full_article.docx",

            "PdfSaveOptions.with_options.pdf",

            save_options=save_options,

        )

        # ExEnd:SaveWithPdfSaveOptions
