# Adapted from aspose.org: knowledge/cells/python/merged/snippets/snippet_007.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_reading_order(self):

        """Test reading order setting."""

        reading_orders = [

            (0, 'Context'),

            (1, 'Left-to-Right'),

            (2, 'Right-to-Left')

        ]

        

        for i, (order, description) in enumerate(reading_orders):

            cell = Cell(f"Reading Order: {description}")

            cell.style.set_reading_order(order)

            self.worksheet.cells[f"G{i+1}"] = cell

            

            # Verify reading order was set correctly

            self.assertEqual(self.worksheet.cells[f"G{i+1}"].style.alignment.reading_order, order)