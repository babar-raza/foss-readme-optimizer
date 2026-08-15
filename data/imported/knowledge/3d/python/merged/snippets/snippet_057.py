# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_057.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_mesh_to_mesh_should_return_same_mesh(self):

        """Test Mesh.ToMesh() returns the same mesh."""

        mesh = Mesh()

        mesh.create_polygon([0, 1, 2])

        

        result = mesh.to_mesh()

        

        self.assertIsNotNone(result)

        self.assertEqual(mesh, result)