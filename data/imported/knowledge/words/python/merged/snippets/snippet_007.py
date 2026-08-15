# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_007.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_open_from_stream_with_load_options(self):

        """Load a document from a stream with explicit LoadOptions."""

        opts = aw.loading.LoadOptions()

        opts.load_format = aw.LoadFormat.DOCX



        with io.FileIO(MY_DIR + "test_full_article.docx") as stream:

            doc = aw.Document(stream, opts)

        assert len(doc.get_text()) > 0