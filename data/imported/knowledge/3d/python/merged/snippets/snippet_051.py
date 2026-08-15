# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_051.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_box_to_mesh_should_create_mesh(self):

        """Test Box.ToMesh() creates a valid mesh."""

        box = Box(10, 20, 30)

        mesh = box.to_mesh()

        

        self.assertIsNotNone(mesh)

        self.assertEqual(8, len(mesh.control_points))