# Adapted from aspose.org: knowledge/cells/python/merged/snippets/snippet_008.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_relative_indent(self):

        """Test relative indent setting."""

        relative_indents = [0, 1, 2, 3, 5]

        

        for i, indent in enumerate(relative_indents):

            cell = Cell(f"Relative Indent: {indent}")

            cell.style.alignment.relative_indent = indent

            self.worksheet.cells[f"H{i+1}"] = cell

            

            # Verify relative indent was set correctly

            self.assertEqual(self.worksheet.cells[f"H{i+1}"].style.alignment.relative_indent, indent)