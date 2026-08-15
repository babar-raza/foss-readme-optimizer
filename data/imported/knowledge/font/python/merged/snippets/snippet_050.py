# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_050.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_glyphs_limit():

    result = run("glyphs", ROBOTO, "--limit", "5")

    assert result.returncode == 0

    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]

    # Header + 5 data rows

    assert len(lines) == 6