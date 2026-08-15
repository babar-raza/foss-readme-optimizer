# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_024.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_array_list_adapter_to_array(self):

        element = VertexElementTemplate[float]()

        element.set_data([1.0, 2.0, 3.0, 4.0])



        arr = element.data.to_array()

        self.assertEqual(4, len(arr))

        self.assertEqual(1.0, arr[0])

        self.assertEqual(2.0, arr[1])

        self.assertEqual(3.0, arr[2])

        self.assertEqual(4.0, arr[3])