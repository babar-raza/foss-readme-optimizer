# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_071.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_gltf_load_options(self):

        options = GltfLoadOptions()

        self.assertIsNotNone(options)

        self.assertTrue(options.flip_tex_coord_v)