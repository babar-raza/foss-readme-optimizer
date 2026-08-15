# Adapted from aspose.org: knowledge/cells/python/merged/snippets/snippet_027.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_border_style_settings(self):

        """Test border line style settings."""

        # Test different border styles

        styles = ['thin', 'medium', 'thick', 'dashed', 'dotted', 'double']

        

        for i, style in enumerate(styles):

            cell = Cell(f"{style.capitalize()} Border")

            cell.style.set_border_style('all', style)

            self.worksheet.cells[f"A{i+1}"] = cell