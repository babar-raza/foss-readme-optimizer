# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_049.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_info_nonexistent_exits_1():

    result = run("info", "/nonexistent_font_file.ttf")

    assert result.returncode == 1

    assert result.stderr.strip() != ""