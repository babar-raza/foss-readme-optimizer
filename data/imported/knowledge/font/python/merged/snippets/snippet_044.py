# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_044.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_version():

    result = run("--version")

    assert result.returncode == 0

    assert "aspose-font" in result.stdout

    assert "1.0.0" in result.stdout