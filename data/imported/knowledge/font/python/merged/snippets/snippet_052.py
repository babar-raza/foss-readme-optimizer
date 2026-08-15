# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_052.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_convert_ttf_to_woff(tmp_path: Path):

    out = str(tmp_path / "out.woff")

    result = run("convert", ROBOTO, out, "--to", "woff")

    assert result.returncode == 0

    assert "Saved:" in result.stdout

    assert Path(out).exists()

    assert Path(out).stat().st_size > 0