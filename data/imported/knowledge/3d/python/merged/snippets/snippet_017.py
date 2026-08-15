# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_017.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_array_list_adapter_contains(self):

        element = VertexElementTemplate[float]()

        element.set_data([1.0, 2.0, 3.0, 4.0])



        self.assertTrue(element.data.contains(2.0))

        self.assertFalse(element.data.contains(5.0))