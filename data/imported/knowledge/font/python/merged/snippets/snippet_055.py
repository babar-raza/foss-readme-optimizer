# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_055.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_metrics_output():

    result = run("metrics", ROBOTO)

    assert result.returncode == 0

    out = result.stdout

    assert "units_per_em:" in out

    assert "ascender:" in out

    assert "descender:" in out