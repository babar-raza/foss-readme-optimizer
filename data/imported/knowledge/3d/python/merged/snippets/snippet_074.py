# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_074.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_gltf_format_properties(self):

        from aspose.threed.formats.gltf import GltfFormat



        gltf_format = GltfFormat()

        self.assertTrue(gltf_format.can_import)

        self.assertTrue(gltf_format.can_export)

        self.assertEqual(gltf_format.version, '2.0')

        self.assertIn('gltf', gltf_format.extensions)

        self.assertIn('glb', gltf_format.extensions)