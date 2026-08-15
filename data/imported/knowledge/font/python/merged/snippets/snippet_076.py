# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_076.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_grid_requires_primary_values(tmp_path: Path):

    out_dir = tmp_path / "preview-grid-none"

    result = run("preview-grid", ROBOTO, str(out_dir), "--axis", "wght")

    assert result.returncode == 1

    assert "requires at least one value" in result.stderr