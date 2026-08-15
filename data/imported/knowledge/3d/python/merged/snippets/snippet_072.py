# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_072.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_gltf_load_options_flip_property(self):

        options = GltfLoadOptions()

        options.flip_tex_coord_v = False

        self.assertFalse(options.flip_tex_coord_v)