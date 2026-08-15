# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_091.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_normals_and_uvs(self):

        obj_content = """# With normals and UVs

v 0.0 0.0 0.0

v 1.0 0.0 0.0

v 1.0 1.0 0.0

v 0.0 1.0 0.0

vt 0.0 0.0

vt 1.0 0.0

vt 1.0 1.0

vt 0.0 1.0

vt 0.0 1.0

vn 0.0 0.0 1.0

f 1/1/1 2/2/1 3/3/1 4/4/1

"""

        scene = Scene()

        stream = io.StringIO(obj_content)

        options = ObjLoadOptions()

        options.file_name = "test.obj"

        

        importer = ObjImporter()

        importer.import_scene(scene, stream, options)

        

        self.assertGreater(len(scene.root_node.child_nodes), 0)

        

        node = scene.root_node.child_nodes[0]

        self.assertIsNotNone(node.entity)

        

        mesh = node.entity

        self.assertEqual(len(mesh.control_points), 4)