# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_076.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_simple_gltf_json(self):

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

                                "POSITION": 0

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

                }

            ],

            "bufferViews": [

                {

                    "buffer": 0,

                    "byteOffset": 0,

                    "byteLength": 36

                }

            ],

            "buffers": [

                {

                    "byteLength": 36,

                    "uri": "data:application/octet-stream;base64,AAAAAAAAAAAAAAAAAACAPwAAAAAAAAAAAAAAAAAAgD8AAAAA"

                }

            ]

        }



        scene = Scene()

        json_str = json.dumps(gltf_data)

        stream = io.BytesIO(json_str.encode('utf-8'))

        options = GltfLoadOptions()



        try:

            from aspose.threed.formats.gltf import GltfImporter

            importer = GltfImporter()

            importer.import_scene(scene, stream, options)



            self.assertEqual(len(scene.root_node.child_nodes), 1)

            node = scene.root_node.child_nodes[0]

            self.assertEqual(node.name, 'TestNode')

            self.assertIsNotNone(node.entity)

        except Exception as e:

            self.fail(f"Failed to import glTF: {e}")