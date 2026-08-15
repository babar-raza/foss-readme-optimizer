# Adapted from aspose.org: knowledge/page/python/merged/snippets/snippet_020.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_run_invokes_server_with_host_port(self) -> None:

        fake = _FakeFastMCP("Aspose.Page")

        with patch("aspose.page.mcp.server.create_server", return_value=fake):

            mcp_server.run(host="0.0.0.0", port=8123)

        self.assertEqual(fake.run_calls, [("0.0.0.0", 8123)])