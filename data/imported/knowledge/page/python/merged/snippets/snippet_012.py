# Adapted from aspose.org: knowledge/page/python/merged/snippets/snippet_012.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_xps_to_bmp_header(self) -> None:

        path = os.path.join("testdata", "xps", "integration", "Simple.xps")

        doc = XpsDocument.from_file(path)

        data = doc.to_image(ImageSaveOptions(format="bmp", dpi=72))

        self.assertTrue(data.startswith(b"BM"))