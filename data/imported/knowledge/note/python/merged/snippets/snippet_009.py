# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_009.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_images_expose_dotnet_compatibility_metadata(self) -> None:

        from aspose.note import Document, Image



        image = Document(self.path).GetChildNodes(Image)[0]



        self.assertEqual(image.OriginalWidth, image.Width)

        self.assertEqual(image.OriginalHeight, image.Height)

        self.assertFalse(hasattr(image, "HorizontalAlignment"))