# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_051.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_glyphs_default_limit():

    result = run("glyphs", ROBOTO)

    assert result.returncode == 0

    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]

    # Header + up to 50 data rows

    assert len(lines) <= 51

    assert len(lines) >= 2  # at least header + 1 glyph
