# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_054.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_richtext_rejects_legacy_keyword_aliases(self) -> None:

        from aspose.note import RichText, TextRun



        with self.assertRaises(TypeError):

            RichText(Runs=[TextRun(Text="segment")])



        with self.assertRaises(TypeError):

            RichText(FontSize=14.0)