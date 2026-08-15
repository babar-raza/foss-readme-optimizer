# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_054.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_pyramid_to_mesh_should_create_mesh(self):

        """Test Pyramid.ToMesh() creates a valid mesh."""

        pyramid = Pyramid(10, 10, 20)

        mesh = pyramid.to_mesh()

        

        self.assertIsNotNone(mesh)

        self.assertGreaterEqual(len(mesh.control_points), 4)