# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_053.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_sphere_to_mesh_should_create_mesh(self):

        """Test Sphere.ToMesh() creates a valid mesh."""

        sphere = Sphere(10, 32, 16)

        mesh = sphere.to_mesh()

        

        self.assertIsNotNone(mesh)

        self.assertGreater(len(mesh.control_points), 0)