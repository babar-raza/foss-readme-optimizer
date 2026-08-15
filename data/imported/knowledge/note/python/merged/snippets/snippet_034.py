# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_034.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_title_hides_composite_child_mutators(self) -> None:

        from aspose.note import RichText, Title



        title = Title(TitleText=RichText(Text="Title"))



        self.assertIs(next(iter(title)), title.TitleText)

        for member in ("FirstChild", "LastChild", "AppendChildFirst", "AppendChildLast", "InsertChild", "RemoveChild"):

            self.assertFalse(hasattr(title, member), member)