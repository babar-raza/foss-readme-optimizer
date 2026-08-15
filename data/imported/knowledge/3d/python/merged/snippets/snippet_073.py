# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_073.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_gltf_format_detection(self):

        from aspose.threed import FileFormat



        gltf_format = FileFormat.get_format_by_extension('.gltf')

        self.assertIsNotNone(gltf_format)

        self.assertEqual(gltf_format.extension, 'gltf')



        glb_format = FileFormat.get_format_by_extension('.glb')

        self.assertIsNotNone(glb_format)