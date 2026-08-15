# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_050.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_richtext_stores_alignment_on_richtext(self) -> None:

        from aspose.note import HorizontalAlignment, ParagraphStyle, RichText



        with self.assertRaises(TypeError):

            ParagraphStyle(Alignment=HorizontalAlignment.Center)



        paragraph_style = ParagraphStyle()

        rich_text = RichText(Text="Aligned", ParagraphStyle=paragraph_style, Alignment=HorizontalAlignment.Center)



        self.assertEqual(rich_text.Alignment, HorizontalAlignment.Center)

        self.assertFalse(hasattr(rich_text.ParagraphStyle, "Alignment"))