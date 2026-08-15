# Adapted from aspose.org: knowledge/cells/python/merged/snippets/snippet_028.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_border_weight_settings(self):

        """Test border line weight settings."""

        # Test different border weights

        weights = [1, 2, 3, 4, 5]

        

        for i, weight in enumerate(weights):

            cell = Cell(f"Weight {weight}")

            cell.style.set_border_weight('all', weight)

            self.worksheet.cells[f"A{i+1}"] = cell