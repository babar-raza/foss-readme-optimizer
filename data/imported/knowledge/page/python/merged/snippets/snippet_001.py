# Adapted from aspose.org: knowledge/page/python/merged/snippets/snippet_001.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_output_path_for(self):

        input_path = Path("testdata/ps/integration/sample.ps")

        output = output_path_for(input_path, ".pdf")

        self.assertEqual(output.as_posix(), "test-out/ps/integration/sample.pdf")