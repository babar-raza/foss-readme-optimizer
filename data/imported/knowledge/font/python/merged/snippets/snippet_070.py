# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_070.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_invalid_axis_exits_1(tmp_path: Path):

    out = tmp_path / "bad-preview.png"

    result = run("preview", ROBOTO, str(out), "--instance", "opsz=12")

    assert result.returncode == 1

    assert "Unknown variable axis" in result.stderr