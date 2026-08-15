# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_028.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_abstract_compatibility_bases_reject_direct_instantiation(self) -> None:

        import aspose.note as note

        from aspose.note import Document, DocumentVisitor, Node, NoteTag, ParagraphStyle



        class CountingVisitor(DocumentVisitor):

            pass



        with self.assertRaises(TypeError):

            Node()



        with self.assertRaises(TypeError):

            DocumentVisitor()



        self.assertFalse(hasattr(note, "CompositeNode"))

        with self.assertRaises(TypeError):

            NoteTag()

        self.assertIsInstance(ParagraphStyle(), ParagraphStyle)

        self.assertIsInstance(Document(), Document)

        self.assertIsInstance(CountingVisitor(), CountingVisitor)