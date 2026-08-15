# Adapted from aspose.org: knowledge/cells/python/merged/snippets/snippet_030.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_mixed_border_settings(self):

        """Test mixed border settings on different sides."""

        cell = Cell("Mixed Borders")

        

        # Set different borders on each side

        cell.style.set_border('top', line_style='thick', color='FFFF0000', weight=3)

        cell.style.set_border('bottom', line_style='medium', color='FF0000FF', weight=2)

        cell.style.set_border('left', line_style='thin', color='FF00FF00', weight=1)

        cell.style.set_border('right', line_style='dashed', color='FF800080', weight=2)

        

        self.worksheet.cells["A1"] = cell