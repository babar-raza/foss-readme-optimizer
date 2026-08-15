# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_006.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_open_from_stream_doc_format(self):

        """Load a .doc document from a stream (auto-detected)."""

        with io.FileIO(MY_DIR + "test_bold.doc") as stream:

            doc = aw.Document(stream)

        assert len(doc.get_text()) > 0