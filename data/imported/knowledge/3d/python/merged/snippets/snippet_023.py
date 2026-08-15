# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_023.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_array_list_adapter_copy_to(self):

        element = VertexElementTemplate[float]()

        element.set_data([1.0, 2.0, 3.0, 4.0])



        array = [0.0] * 4

        element.data.copy_to(array)

        self.assertEqual(1.0, array[0])

        self.assertEqual(2.0, array[1])

        self.assertEqual(3.0, array[2])

        self.assertEqual(4.0, array[3])