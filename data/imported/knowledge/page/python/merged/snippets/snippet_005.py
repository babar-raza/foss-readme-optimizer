# Adapted from aspose.org: knowledge/page/python/merged/snippets/snippet_005.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_skip_without_tools(self):

        with EnvGuard(PDF_COMPARE_CMD="", PDF_RENDER_CMD=""):

            with self.assertRaises(unittest.SkipTest):

                compare_pdfs(Path("baseline.pdf"), Path("actual.pdf"))