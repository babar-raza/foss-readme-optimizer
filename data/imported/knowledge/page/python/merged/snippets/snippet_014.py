# Adapted from aspose.org: knowledge/page/python/merged/snippets/snippet_014.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_ps_to_image_requires_format(self) -> None:

        ps_bytes = b"%!PS-Adobe-3.0\n0 0 moveto 10 0 lineto stroke\n"

        input_payload = McpInput(input_path=None, input_bytes_b64=base64.b64encode(ps_bytes).decode("ascii"))

        output = McpOutput(output_path=None, return_bytes=True)

        with self.assertRaises(ValueError):

            ps_to_image(input_payload, output, McpConversionOptions(format=None, dpi=72))