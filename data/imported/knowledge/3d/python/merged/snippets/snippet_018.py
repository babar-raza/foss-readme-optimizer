# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_018.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_array_list_adapter_remove(self):

        element = VertexElementTemplate[float]()

        element.set_data([1.0, 2.0, 3.0, 4.0])



        result = element.data.remove(2.0)

        self.assertTrue(result)

        self.assertEqual(3, len(element.data))

        self.assertFalse(element.data.contains(2.0))