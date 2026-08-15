# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_079.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_material_properties_from_corset(self):

        scene = Scene()

        options = GltfLoadOptions()

        scene.open('examples/gltf2/Corset/glTF/Corset.gltf', options)



        node = scene.root_node.child_nodes[0]

        if node and node.material:

            material = node.material

            self.assertIsInstance(material, PbrMaterial)

            self.assertEqual(material.name, 'Corset_O')



            from aspose.threed.utilities import Vector3

            self.assertEqual(material.metallic_factor, 0.0)

            self.assertEqual(material.roughness_factor, 1.0)