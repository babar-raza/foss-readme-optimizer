# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_052.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_cylinder_to_mesh_should_create_mesh(self):

        """Test Cylinder.ToMesh() creates a valid mesh."""

        cylinder = Cylinder(5, 5, 20)

        mesh = cylinder.to_mesh()

        

        self.assertIsNotNone(mesh)

        self.assertGreater(len(mesh.control_points), 0)