# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_072.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_batch_selected_names_and_default(tmp_path: Path):

    out_dir = tmp_path / "preview-batch-selected"

    result = run(

        "preview-batch",

        ROBOTO,

        str(out_dir),

        "--instance-name",

        "Bold",

        "--include-default",

    )

    assert result.returncode == 0

    files = sorted(path.name for path in out_dir.glob("*.png"))

    assert files == ["roboto-instance-bold.png", "roboto-instance-regular.png"]