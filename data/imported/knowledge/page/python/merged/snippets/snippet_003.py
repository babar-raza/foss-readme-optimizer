# Adapted from aspose.org: knowledge/page/python/merged/snippets/snippet_003.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_skip_when_missing(self):

        with EnvGuard(PDF_VALIDATOR_CMD=""):

            with self.assertRaises(unittest.SkipTest):

                validate_pdf(Path("dummy.pdf"))