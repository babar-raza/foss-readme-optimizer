# Adapted from aspose.org: knowledge/cells/python/merged/snippets/snippet_003.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_text_wrap(self):

        """Test text wrap setting."""

        # Test wrap text enabled

        cell1 = Cell("Text Wrap Enabled")

        cell1.style.set_text_wrap(True)

        self.worksheet.cells["C1"] = cell1

        self.assertTrue(self.worksheet.cells["C1"].style.alignment.wrap_text)

        

        # Test wrap text disabled

        cell2 = Cell("Text Wrap Disabled")

        cell2.style.set_text_wrap(False)

        self.worksheet.cells["C2"] = cell2

        self.assertFalse(self.worksheet.cells["C2"].style.alignment.wrap_text)