# Adapted from aspose.org: knowledge/cells/python/merged/snippets/snippet_047.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_set_comment_size_separately(self):

        """Test setting comment size after creating comment."""

        wb = Workbook()

        ws = wb.worksheets[0]



        # Set comment without size

        ws.cells['B2'].value = "Cell B2"

        ws.cells['B2'].set_comment("Initial comment", "Author2")



        # Set size separately

        ws.cells['B2'].set_comment_size(180, 120)



        # Verify size

        size = ws.cells['B2'].get_comment_size()

        self.assertEqual(size[0], 180)

        self.assertEqual(size[1], 120)



        print("Test: Set comment size separately - PASSED")