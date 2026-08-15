# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_088.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_waterfall_requires_instance_selection(tmp_path: Path):

    out = tmp_path / "waterfall.png"

    result = run("preview-waterfall", ROBOTO, str(out))

    assert result.returncode == 1

    assert "requires --all-named, --include-default, or at least one --instance-name" in result.stderr