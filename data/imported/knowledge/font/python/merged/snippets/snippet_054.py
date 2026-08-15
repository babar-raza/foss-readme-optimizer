# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_054.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_convert_ttf_to_eot(tmp_path: Path):

    out = str(tmp_path / "out.eot")

    result = run("convert", ROBOTO, out, "--to", "eot")

    assert result.returncode == 0

    assert Path(out).exists()

    loaded = FontLoader.open(out)

    assert isinstance(loaded, EotFont)