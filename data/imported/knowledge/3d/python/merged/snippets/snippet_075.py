# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_075.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_gltf_plugin_registered(self):

        from aspose.threed.formats import IOService

        from aspose.threed.formats.gltf import GltfPlugin



        io_service = IOService()

        gltf_plugin = io_service.get_plugin_for_extension('.gltf')

        self.assertIsNotNone(gltf_plugin)

        self.assertIsInstance(gltf_plugin, GltfPlugin)