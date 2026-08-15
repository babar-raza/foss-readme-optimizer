# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_032.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_import_real_cube(self):

        scene = Scene()

        options = ColladaLoadOptions()



        file_path = os.path.join(os.path.dirname(__file__), '..', 'examples', 'collada', 'cube_triangulate.dae')

        

        if os.path.exists(file_path):

            scene.open(file_path, options)



            self.assertIsNotNone(scene.root_node)

            self.assertTrue(len(scene.root_node.child_nodes) > 0)

        else:

            self.skipTest(f"File not found: {file_path}")