# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_012.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_array_list_adapter_float(self):

        element = VertexElementTemplate[float]()

        element.set_data([1.0, 2.0, 3.0, 4.0])



        data = element.data

        self.assertEqual(4, len(data))

        self.assertEqual(1.0, data[0])

        self.assertEqual(2.0, data[1])

        self.assertEqual(3.0, data[2])

        self.assertEqual(4.0, data[3])