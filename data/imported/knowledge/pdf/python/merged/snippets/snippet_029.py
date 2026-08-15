# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_029.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_bundle_is_deterministic() -> None:

    """The checked-in bundle matches a fresh build (SHA-verified generator)."""

    script = Path(__file__).resolve().parents[1] / "scripts" / "build_agl_data.py"

    result = subprocess.run(

        [sys.executable, str(script), "--check"],

        capture_output=True,

        text=True,

    )

    assert result.returncode == 0, result.stderr + result.stdout