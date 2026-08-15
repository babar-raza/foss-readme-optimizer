# Adapted from aspose.org: knowledge/cells/python/merged/snippets/snippet_040.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_double_values(self):

        """Test setting and saving double/float values."""

        test_values = [0.0, 1.5, -2.7, 3.14159, 0.0001, -999.999]

        

        for i, value in enumerate(test_values):

            cell = Cell(value)

            self.worksheet.cells[f"B{i+1}"] = cell

            

            # Verify the value was set correctly

            self.assertEqual(self.worksheet.cells[f"B{i+1}"].value, value)

            self.assertIsInstance(self.worksheet.cells[f"B{i+1}"].value, float)