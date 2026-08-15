# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_003.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_open_document_from_file(self):

        """Load a document from a file path string."""

        # ExStart:OpenDocument

        doc = aw.Document(MY_DIR + "test_full_article.docx")

        # ExEnd:OpenDocument

        assert len(doc.get_text()) > 0