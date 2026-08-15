# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_088.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_basic_cube_import(self):

        obj_content = """# Simple cube OBJ

v 0.0 0.0 0.0

v 1.0 0.0 0.0

v 1.0 1.0 0.0

v 0.0 1.0 0.0

f 1 2 3 4

f 5 6 7 8

"""

        scene = Scene()

        stream = io.StringIO(obj_content)

        options = ObjLoadOptions()

        options.file_name = "test.obj"

        

        importer = ObjImporter()

        importer.import_scene(scene, stream, options)

        

        self.assertIsNotNone(scene.root_node)

        self.assertGreater(len(scene.root_node.child_nodes), 0)

        

        node = scene.root_node.child_nodes[0]

        self.assertIsNotNone(node.entity)

        

        mesh = node.entity

        self.assertEqual(len(mesh.control_points), 8)

        self.assertEqual(mesh.polygon_count, 2)