# Adapted from aspose.org: knowledge/page/python/merged/snippets/snippet_019.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_create_server_registers_all_tools(self) -> None:

        fake_module = types.ModuleType("fastmcp")

        fake_module.FastMCP = _FakeFastMCP



        with patch.dict(sys.modules, {"fastmcp": fake_module}):

            server = mcp_server.create_server()



        self.assertEqual(server.name, "Aspose.Page")

        self.assertEqual(

            [tool.__name__ for tool in server.tools],

            ["ps_to_pdf", "ps_to_image", "xps_to_pdf", "xps_to_image", "eps_metadata"],

        )