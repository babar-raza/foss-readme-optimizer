# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_009.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_open_and_save(self):

        """Load from stream, then save to file."""

        with io.FileIO(MY_DIR + "test_full_article.docx") as stream:

            doc = aw.Document(stream)



        doc.save(ARTIFACTS_DIR + "LoadingDocument.OpenAndSave.md", aw.SaveFormat.MARKDOWN)

        assert Path(ARTIFACTS_DIR + "LoadingDocument.OpenAndSave.md").exists()