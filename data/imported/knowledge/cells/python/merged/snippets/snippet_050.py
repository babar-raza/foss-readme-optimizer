# Adapted from aspose.org: knowledge/cells/python/merged/snippets/snippet_050.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_error_on_size_without_comment(self):

        """Test that setting size without a comment raises an error."""

        wb = Workbook()

        ws = wb.worksheets[0]



        ws.cells['A1'].value = "No comment"



        with self.assertRaises(ValueError) as context:

            ws.cells['A1'].set_comment_size(100, 100)



        self.assertIn("has no comment", str(context.exception))

        print("Test: Error on size without comment - PASSED")