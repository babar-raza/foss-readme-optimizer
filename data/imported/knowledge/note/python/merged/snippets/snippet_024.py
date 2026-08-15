# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_024.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_accept_visits_document_and_pages(self) -> None:

        from aspose.note import Document, DocumentVisitor, Page



        class CountingVisitor(DocumentVisitor):

            def __init__(self) -> None:

                self.pages = 0

                self.doc_start = 0



            def VisitDocumentStart(self, document):  # noqa: N802

                self.doc_start += 1



            def VisitPageStart(self, page: Page):  # noqa: N802

                self.pages += 1



        doc = Document(self.path)

        v = CountingVisitor()

        doc.Accept(v)



        self.assertEqual(v.doc_start, 1)

        self.assertGreaterEqual(v.pages, 1)