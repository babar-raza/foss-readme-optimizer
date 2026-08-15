# Adapted from aspose.org: knowledge/page/python/merged/snippets/snippet_002.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_baseline_map(self):

        with EnvGuard(BASELINE_MAP="ps/images=/tmp/baselines"):

            baseline = baseline_path_for(Path("testdata/ps/images/foo.png"), ".eps")

            self.assertEqual(baseline.as_posix(), "/tmp/baselines/foo.eps")