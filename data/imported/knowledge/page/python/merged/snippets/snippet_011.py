# Adapted from aspose.org: knowledge/page/python/merged/snippets/snippet_011.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_encode_jpeg_non_empty(self) -> None:

        doc = RenderDocument()

        doc.pages.append(RenderPage(width=8, height=8))

        surface = RasterRenderer(dpi=72).render(doc)

        jpeg = encode_jpeg(surface)

        self.assertTrue(jpeg.startswith(b"\xFF\xD8"))

        self.assertGreater(len(jpeg), 4)