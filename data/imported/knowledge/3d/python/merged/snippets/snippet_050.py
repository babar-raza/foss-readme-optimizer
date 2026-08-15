# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_050.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_file_format_create_options(self):

        file_format = FileFormat()

        load_options = file_format.create_load_options()

        save_options = file_format.create_save_options()

        

        self.assertIsInstance(load_options, LoadOptions)

        self.assertIsInstance(save_options, SaveOptions)

        self.assertEqual(load_options.file_format, file_format)

        self.assertEqual(save_options.file_format, file_format)