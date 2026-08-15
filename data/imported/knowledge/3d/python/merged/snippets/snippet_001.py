# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_001.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_save_options(self):

        options = self.plugin.create_save_options()

        self.assertIsInstance(options, ThreeMfSaveOptions)

        self.assertTrue(options.enable_compression)

        self.assertTrue(options.build_all)

        self.assertFalse(options.flip_coordinate_system)

        

        options.enable_compression = False

        self.assertFalse(options.enable_compression)

        

        options.flip_coordinate_system = True

        self.assertTrue(options.flip_coordinate_system)