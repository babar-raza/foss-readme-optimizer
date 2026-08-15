# Adapted from aspose.org: knowledge/cells/python/merged/snippets/snippet_001.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_horizontal_alignment(self):

        """Test horizontal alignment settings."""

        horizontal_alignments = [

            'general',

            'left',

            'center',

            'right',

            'fill',

            'justify',

            'centerContinuous',

            'distributed'

        ]

        

        for i, alignment in enumerate(horizontal_alignments):

            cell = Cell(f"Horizontal: {alignment}")

            cell.style.set_horizontal_alignment(alignment)

            self.worksheet.cells[f"A{i+1}"] = cell

            

            # Verify alignment was set correctly

            self.assertEqual(self.worksheet.cells[f"A{i+1}"].style.alignment.horizontal, alignment)