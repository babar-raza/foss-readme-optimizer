# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_062.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_export_with_positions(self):

        scene = Scene()

        mesh = Mesh('TestMesh')



        mesh._control_points.append(Vector4(0.0, 0.0, 0.0, 1.0))

        mesh._control_points.append(Vector4(1.0, 0.0, 0.0, 1.0))

        mesh._control_points.append(Vector4(0.0, 1.0, 0.0, 1.0))

        mesh.create_polygon(0, 1, 2)



        scene.root_node.create_child_node('TestNode').entity = mesh



        stream = io.BytesIO()

        options = GltfSaveOptions()

        options.binary_mode = False

        options.file_name = 'test.gltf'



        from aspose.threed.formats.gltf import GltfExporter

        exporter = GltfExporter()

        exporter.export(scene, stream, options)



        stream.seek(0)

        content = stream.read()

        gltf_data = json.loads(content.decode('utf-8'))



        self.assertGreater(len(gltf_data['meshes']), 0)

        mesh_data = gltf_data['meshes'][0]

        self.assertIn('primitives', mesh_data)

        self.assertIn('POSITION', mesh_data['primitives'][0]['attributes'])