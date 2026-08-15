# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_046.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_save_options_creation(self):

        options = SaveOptions()

        self.assertIsNotNone(options)

        self.assertFalse(options.export_textures)