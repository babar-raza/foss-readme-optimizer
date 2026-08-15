# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_012.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_tables_exposed_with_rows_and_cells(self) -> None:

        from aspose.note import Document, Table, TableRow, TableCell



        doc = Document(self.path)

        tables = doc.GetChildNodes(Table)

        self.assertGreaterEqual(len(tables), 1)



        rows = doc.GetChildNodes(TableRow)

        cells = doc.GetChildNodes(TableCell)

        self.assertGreater(len(rows), 0)

        self.assertGreater(len(cells), 0)



        # Basic structural sanity: each TableRow should have at least 1 cell.

        for row in rows[:10]:

            self.assertGreaterEqual(len(list(row)), 1)