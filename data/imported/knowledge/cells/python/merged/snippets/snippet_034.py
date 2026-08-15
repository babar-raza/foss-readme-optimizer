# Adapted from aspose.org: knowledge/cells/python/merged/snippets/snippet_034.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_save_border_settings(self):

        """Test saving border settings to file."""

        # Create comprehensive test data

        self.test_comprehensive_border_test()

        

        # Save to outputfiles folder

        output_path = examples_output_path('example_test_border_settings.xlsx')

        

        self.workbook.save(output_path)

        

        # Verify file was created

        self.assertTrue(os.path.exists(output_path))

        

        # Verify file is not empty

        file_size = os.path.getsize(output_path)

        self.assertGreater(file_size, 0)

        

        print(f"Border settings test file saved to: {output_path}")

        print(f"File size: {file_size} bytes")