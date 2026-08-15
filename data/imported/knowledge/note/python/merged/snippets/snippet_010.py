# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_010.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_image_uses_alignment_without_legacy_alias(self) -> None:

        from aspose.note import HorizontalAlignment, Image



        image = Image(Bytes=b"img", Width=10.0, Height=20.0, Alignment=HorizontalAlignment.Center)



        self.assertEqual(image.Alignment, HorizontalAlignment.Center)

        self.assertFalse(hasattr(image, "HorizontalAlignment"))