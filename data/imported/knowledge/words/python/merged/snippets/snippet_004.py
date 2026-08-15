# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_004.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_open_document_from_file_doc_format(self):

        """Load a .doc file from a file path string."""

        doc = aw.Document(MY_DIR + "test_bold.doc")

        assert len(doc.get_text()) > 0