# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_027.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_get_text(self):

        """Extract text via get_text() without saving to file."""

        # ExStart:GetText

        doc = aw.Document(MY_DIR + "test_full_article.docx")

        text = doc.get_text()

        assert len(text) > 0

        # ExEnd:GetText
