# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_010.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_load_markdown_from_bytes(self):

        # ExStart:LoadMarkdownFromBytes

        doc = aw.Document(io.BytesIO(MARKDOWN_TEXT.encode("utf-8")), aw.loading.MarkdownLoadOptions())

        # ExEnd:LoadMarkdownFromBytes

        assert "Release Notes" in doc.get_text()