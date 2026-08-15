# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_011.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_load_markdown_from_stream(self):

        # ExStart:LoadMarkdownFromStream

        with io.BytesIO(MARKDOWN_TEXT.encode("utf-8")) as stream:

            doc = aw.Document(stream, aw.loading.MarkdownLoadOptions())

        # ExEnd:LoadMarkdownFromStream

        assert "def add" in doc.get_text()