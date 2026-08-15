# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_008.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_images_preserve_outline_alignment(self) -> None:

        from aspose.note import Document, HorizontalAlignment, Image



        doc = Document(self.path)

        images = doc.GetChildNodes(Image)



        self.assertEqual(

            [image.Alignment for image in images],

            [

                HorizontalAlignment.Right,

                HorizontalAlignment.Center,

                HorizontalAlignment.Left,

            ],

        )