# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_097.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_obj_format_detection(self):

        obj_format = ObjFormat()

        self.assertTrue(obj_format.can_import)

        self.assertFalse(obj_format.can_export)

        self.assertEqual(obj_format.extension, "obj")

        self.assertIn("obj", obj_format.extensions)