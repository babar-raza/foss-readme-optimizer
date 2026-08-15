# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_031.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_collada_format_can_export(self):

        from aspose.threed.formats.collada.ColladaFormat import ColladaFormat



        collada_format = ColladaFormat()

        self.assertTrue(collada_format.can_export)