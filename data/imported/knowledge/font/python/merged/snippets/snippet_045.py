# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_045.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_info_prints_metadata():

    result = run("info", ROBOTO)

    assert result.returncode == 0

    out = result.stdout

    assert "TTF" in out

    assert "Roboto" in out

    assert "Glyphs:" in out

    assert "Units/EM:" in out