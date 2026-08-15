# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_029.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_encrypted_load_raises_incorrect_password(self) -> None:

        from aspose.note import Document, IncorrectPasswordException, LoadOptions



        p = _fixture_path("FormattedRichText.one")

        if p is None:

            raise unittest.SkipTest("FormattedRichText.one not found")



        with self.assertRaises(IncorrectPasswordException):

            Document(p, LoadOptions(DocumentPassword="pass"))