# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_100.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_get_plugin_by_format(self):

        from aspose.threed.formats.obj import ObjFormat

        from aspose.threed.formats.stl import StlFormat



        io_service = IOService()

        obj_fmt = ObjFormat()

        stl_fmt = StlFormat()

        threemf_fmt = io_service.get_plugin_for_extension('.3mf').get_file_format()



        obj_plugin = io_service.get_plugin_for_format(obj_fmt)

        stl_plugin = io_service.get_plugin_for_format(stl_fmt)

        threemf_plugin = io_service.get_plugin_for_format(threemf_fmt)

        

        obj_plugin_class = type(obj_plugin)

        stl_plugin_class = type(stl_plugin)

        threemf_plugin_class = type(threemf_plugin)

        

        self.assertIsInstance(obj_plugin, obj_plugin_class)

        self.assertIsInstance(stl_plugin, stl_plugin_class)

        self.assertIsInstance(threemf_plugin, threemf_plugin_class)