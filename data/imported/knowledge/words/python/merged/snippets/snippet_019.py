# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_019.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_markdown_from_all_input_formats(self):

        """Save DOC, DOCX, RTF, TXT as Markdown with default options."""

        inputs = {

            "docx": "test_full_article.docx",

            "doc": "test_full_article.doc",

            "rtf": "test_full_article.rtf",

            "txt": "test_plain.txt",

        }

        save_options = aw.saving.MarkdownSaveOptions()

        for label, filename in inputs.items():

            self.convert(

                filename,

                f"MarkdownSaveOptions.from_{label}.md",

                save_options=save_options,

            )