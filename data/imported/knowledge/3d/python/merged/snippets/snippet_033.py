# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_033.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_collada_load_options(self):

        options = ColladaLoadOptions()



        self.assertEqual(options.flip_coordinate_system, False)



        options.flip_coordinate_system = True

        self.assertEqual(options.flip_coordinate_system, True)