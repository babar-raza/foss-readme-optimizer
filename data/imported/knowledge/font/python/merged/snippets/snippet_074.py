# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_074.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_batch_requires_selection(tmp_path: Path):

    out_dir = tmp_path / "preview-batch-none"

    result = run("preview-batch", ROBOTO, str(out_dir))

    assert result.returncode == 1

    assert "requires --all-named or at least one --instance-name" in result.stderr