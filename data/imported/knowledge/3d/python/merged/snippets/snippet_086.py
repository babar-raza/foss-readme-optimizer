# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_086.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_non_triangle_mesh_triangulated(self):

        scene = Scene()

        

        mesh = Mesh("quad_mesh")

        mesh._control_points = [

            Vector4(0.0, 0.0, 0.0, 1.0),

            Vector4(1.0, 0.0, 0.0, 1.0),

            Vector4(1.0, 1.0, 0.0, 1.0),

            Vector4(0.0, 1.0, 0.0, 1.0),

        ]

        mesh.create_polygon(0, 1, 2, 3)

        

        node = Node("node")

        node.entity = mesh

        node.parent_node = scene.root_node

        

        stream = io.StringIO()

        options = StlSaveOptions()

        options.binary_mode = False

        

        exporter = StlExporter()

        exporter.export(scene, stream, options)

        

        content = stream.getvalue()

        facet_count = content.count("facet normal")

        self.assertEqual(facet_count, 2)