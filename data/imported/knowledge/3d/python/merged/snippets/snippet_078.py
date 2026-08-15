# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_078.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_material_import_from_boombox(self):

        scene = Scene()

        options = GltfLoadOptions()

        scene.open('examples/gltf2/BoomBox/glTF/BoomBox.gltf', options)



        self.assertEqual(len(scene.root_node.child_nodes), 1)



        node = scene.root_node.child_nodes[0]

        self.assertIsNotNone(node.material)

        self.assertIsInstance(node.material, PbrMaterial)



        material = node.material

        self.assertEqual(material.name, 'BoomBox_Mat')



        from aspose.threed.utilities import Vector3

        self.assertEqual(material.albedo, Vector3(1.0, 1.0, 1.0))

        self.assertEqual(material.metallic_factor, 0.0)

        self.assertEqual(material.roughness_factor, 1.0)

        self.assertEqual(material.transparency, 0.0)