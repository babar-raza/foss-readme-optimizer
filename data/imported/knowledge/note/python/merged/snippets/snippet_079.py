# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_079.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_image_with_tag_exposes_tags(self) -> None:

        p = _fixture_path("ImageWithTag.one")

        if p is None:

            raise unittest.SkipTest("ImageWithTag.one not found")



        from aspose.note import Document, Image



        doc = Document(p)

        images = doc.GetChildNodes(Image)

        self.assertGreaterEqual(len(images), 1)



        tagged = [img for img in images if getattr(img, "Tags", None)]

        self.assertGreaterEqual(len(tagged), 1)

        self.assertTrue(any(_tag_is_meaningful(t) for img in tagged for t in img.Tags))