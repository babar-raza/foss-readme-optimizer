# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_030.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_collada_save_options(self):

        options = ColladaSaveOptions()



        self.assertEqual(options.flip_coordinate_system, False)

        self.assertEqual(options.enable_materials, True)

        self.assertEqual(options.indented, True)



        options.flip_coordinate_system = True

        self.assertEqual(options.flip_coordinate_system, True)



        options.indented = False

        self.assertEqual(options.indented, False)