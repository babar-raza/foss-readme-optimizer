# Adapted from aspose.org: knowledge/cells/python/merged/snippets/snippet_042.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_formula_values(self):

        """Test setting and saving formula values."""

        test_formulas = [

            "=SUM(A1:A5)",

            "=A1+B1",

            "=IF(A1>0, \"Positive\", \"Non-positive\")",

            "=VLOOKUP(A1, B1:C10, 2, FALSE)",

            "=AVERAGE(A1:A10)",

            "=MAX(A1:A5)",

            "=MIN(A1:A5)",

            "=COUNT(A1:A10)"

        ]

        

        for i, formula in enumerate(test_formulas):

            cell = Cell(None, formula)

            self.worksheet.cells[f"D{i+1}"] = cell

            

            # Verify the formula was set correctly

            self.assertEqual(self.worksheet.cells[f"D{i+1}"].formula, formula)

            self.assertIsNone(self.worksheet.cells[f"D{i+1}"].value)