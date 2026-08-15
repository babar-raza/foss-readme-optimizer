# Adapted from aspose.org: knowledge/page/python/merged/snippets/snippet_004.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_compare_images(self):

        try:

            from PIL import Image  # type: ignore

        except Exception:

            with EnvGuard(IMAGE_COMPARE_CMD=""):

                with self.assertRaises(unittest.SkipTest):

                    compare_images(Path("missing.png"), Path("missing.png"))

            return

        with tempfile.TemporaryDirectory() as tmpdir:

            baseline = Path(tmpdir) / "base.png"

            actual = Path(tmpdir) / "actual.png"

            Image.new("RGB", (4, 4), color=(10, 20, 30)).save(baseline)

            Image.new("RGB", (4, 4), color=(10, 20, 30)).save(actual)

            compare_images(baseline, actual, delta=1, ratio=0.0)