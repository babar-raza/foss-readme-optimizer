# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_018.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_set_paragraph_break(self):

        # ExStart:SetParagraphBreak

        save_options = aw.saving.MarkdownSaveOptions()

        save_options.paragraph_break = "\r\n"



        self.convert(

            "test_full_article.docx",

            "MarkdownSaveOptions.paragraph_break_crlf.md",

            save_options=save_options,

        )

        # ExEnd:SetParagraphBreak



        output = Path(ARTIFACTS_DIR) / "MarkdownSaveOptions.paragraph_break_crlf.md"

        content = output.read_bytes()

        assert b"\r\n" in content, "CRLF line endings expected"