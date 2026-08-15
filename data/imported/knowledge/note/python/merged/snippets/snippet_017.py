# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_017.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_construct_from_stream(self) -> None:

        from aspose.note import Document



        doc = Document(io.BytesIO(self.data))

        self.assertGreater(len(list(doc)), 0)