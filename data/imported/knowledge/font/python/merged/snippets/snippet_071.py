# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_071.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_batch_all_named_writes_multiple_pngs(tmp_path: Path):

    out_dir = tmp_path / "preview-batch-all"

    result = run("preview-batch", ROBOTO, str(out_dir), "--all-named", "--text", "Batch CLI Preview")

    assert result.returncode == 0

    files = sorted(path.name for path in out_dir.glob("*.png"))

    source = FontLoader.open(ROBOTO)

    assert len(files) == len(source.variable_instances)

    assert "roboto-instance-bold.png" in files

    assert "Written:" in result.stdout