# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_045.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_load_options_creation(self):

        options = LoadOptions()

        self.assertIsNotNone(options)

        self.assertIsNone(options.encoding)

        self.assertIsNone(options.file_name)

        self.assertEqual(options.lookup_paths, [])