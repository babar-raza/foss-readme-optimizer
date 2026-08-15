# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_002.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_get_text_from_all_formats(self):

        """Extract plain text via get_text() from every input format."""

        for in_label, in_file in INPUT_FILES.items():

            doc = aw.Document(MY_DIR + in_file)

            text = doc.get_text()

            assert len(text) > 0, f"get_text() returned empty for {in_file}"