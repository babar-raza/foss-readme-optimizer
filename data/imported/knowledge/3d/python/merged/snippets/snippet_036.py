# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_036.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_materials_always_loaded(self):

        options = ColladaLoadOptions()



        file_path = os.path.join(os.path.dirname(__file__), '..', 'examples', 'collada', 'cube_triangulate.dae')

        

        if os.path.exists(file_path):

            scene = Scene()

            scene.open(file_path, options)



            self.assertIsNotNone(scene.root_node)



            box_node = None

            for node in scene.root_node.child_nodes:

                if node.name == 'Box':

                    box_node = node

                    break



            self.assertIsNotNone(box_node)

            self.assertIsNotNone(box_node.material)

        else:

            self.skipTest(f"File not found: {file_path}")