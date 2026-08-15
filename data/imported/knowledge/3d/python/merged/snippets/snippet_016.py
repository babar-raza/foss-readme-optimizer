# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_016.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_array_list_adapter_add(self):

        element = VertexElementTemplate[float]()

        element.data.add(1.0)

        element.data.add(2.0)

        element.data.add(3.0)



        self.assertEqual(3, len(element.data))

        self.assertEqual(1.0, element.data[0])

        self.assertEqual(2.0, element.data[1])

        self.assertEqual(3.0, element.data[2])