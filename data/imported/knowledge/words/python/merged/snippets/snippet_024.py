# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_024.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_pdf_from_all_input_formats(self):

        """Save DOCX, DOC, RTF, TXT as PDF."""

        inputs = {

            "docx": "test_full_article.docx",

            "doc": "test_full_article.doc",

            "rtf": "test_full_article.rtf",

            "txt": "test_plain.txt",

        }

        for label, filename in inputs.items():

            self.convert(

                filename, f"PdfSaveOptions.from_{label}.pdf", save_format=aw.SaveFormat.PDF

            )