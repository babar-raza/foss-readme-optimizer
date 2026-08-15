# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_047.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_load_options_properties(self):

        options = LoadOptions()

        options.encoding = 'utf-8'

        options.file_name = 'test.obj'

        options.lookup_paths = ['/path1', '/path2']

        

        self.assertEqual(options.encoding, 'utf-8')

        self.assertEqual(options.file_name, 'test.obj')

        self.assertEqual(options.lookup_paths, ['/path1', '/path2'])