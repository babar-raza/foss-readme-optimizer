# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_003.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_format_detection(self):

        self.assertEqual(self.format.extension, '3mf')

        self.assertIn('3mf', self.format.extensions)

        self.assertTrue(self.format.can_import)

        self.assertTrue(self.format.can_export)