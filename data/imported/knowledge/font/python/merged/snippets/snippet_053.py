# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_053.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_convert_bad_format(tmp_path: Path):

    out = str(tmp_path / "out.xyz")

    result = run("convert", ROBOTO, out, "--to", "xyz")

    assert result.returncode == 1

    assert result.stderr.strip() != ""