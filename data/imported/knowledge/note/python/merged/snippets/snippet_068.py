# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_068.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_question_tag_uses_distinct_color(self) -> None:

        from aspose.note.saving.pdf_writer import _tag_color



        self.assertEqual(_tag_color(15), (0.64, 0.32, 0.82))

        self.assertNotEqual(_tag_color(15), _tag_color(13))