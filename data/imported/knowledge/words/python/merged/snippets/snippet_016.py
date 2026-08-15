# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_016.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_export_underline_formatting(self):

        # ExStart:ExportUnderlineFormatting

        save_options = aw.saving.MarkdownSaveOptions()

        save_options.export_underline_formatting = True



        self.convert(

            "test_underline_text.docx",

            "MarkdownSaveOptions.export_underline.md",

            save_options=save_options,

        )

        # ExEnd:ExportUnderlineFormatting
