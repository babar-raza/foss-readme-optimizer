# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_058.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_normals_loading(self):

        gltf_data = {

            "asset": {

                "version": "2.0",

                "generator": "test"

            },

            "scene": 0,

            "scenes": [

                {

                    "nodes": [0]

                }

            ],

            "nodes": [

                {

                    "name": "TestNode",

                    "mesh": 0

                }

            ],

            "meshes": [

                {

                    "name": "TestMesh",

                    "primitives": [

                        {

                            "attributes": {

                                "POSITION": 0,

                                "NORMAL": 1

                            },

                            "mode": 4

                        }

                    ]

                }

            ],

            "accessors": [

                {

                    "bufferView": 0,

                    "componentType": 5126,

                    "count": 3,

                    "type": "VEC3"

                },

                {

                    "bufferView": 1,

                    "componentType": 5126,

                    "count": 3,

                    "type": "VEC3"

                }

            ],

            "bufferViews": [

                {

                    "buffer": 0,

                    "byteOffset": 0,

                    "byteLength": 36

                },

                {

                    "buffer": 0,

                    "byteOffset": 36,

                    "byteLength": 36

                }

            ],

            "buffers": [

                {

                    "byteLength": 72,

                    "uri": "data:application/octet-stream;base64,AAAAAAAAAAAAAAAAAACAPwAAAAAAAAAAAAAAAAAAgD8AAAAAAAAAAAAAAAAAAIA/AAAAAAAAAAAAAIA/AAAAAAAAAAAAAIA/"

                }

            ]

        }



        scene = Scene()

        json_str = json.dumps(gltf_data)

        stream = io.BytesIO(json_str.encode('utf-8'))

        options = GltfLoadOptions()



        from aspose.threed.formats.gltf import GltfImporter

        importer = GltfImporter()

        importer.import_scene(scene, stream, options)



        self.assertEqual(len(scene.root_node.child_nodes), 1)

        node = scene.root_node.child_nodes[0]

        self.assertIsNotNone(node.entity)



        from aspose.threed.entities import VertexElementNormal

        has_normals = False

        for element in node.entity.vertex_elements:

            if isinstance(element, VertexElementNormal):

                has_normals = True

                self.assertEqual(len(element.data), 3)



        self.assertTrue(has_normals, "Mesh should have VertexElementNormal")