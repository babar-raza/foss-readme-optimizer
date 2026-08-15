# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_049.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_textstyle_rejects_legacy_keyword_aliases(self) -> None:

        from aspose.note import TextStyle



        for kwargs in (

            {"Bold": True},

            {"Italic": True},

            {"Underline": True},

            {"Strikethrough": True},

            {"Superscript": True},

            {"Subscript": True},

            {"HighlightColor": 123},

            {"LanguageId": 1031},

        ):

            with self.subTest(kwargs=kwargs):

                with self.assertRaises(TypeError):

                    TextStyle(**kwargs)