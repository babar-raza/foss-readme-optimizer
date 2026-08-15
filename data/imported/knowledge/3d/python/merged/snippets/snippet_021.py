# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_021.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_array_list_adapter_insert(self):

        element = VertexElementTemplate[float]()

        element.set_data([1.0, 3.0, 4.0])



        element.data.insert(1, 2.0)

        self.assertEqual(4, len(element.data))

        self.assertEqual(2.0, element.data[1])