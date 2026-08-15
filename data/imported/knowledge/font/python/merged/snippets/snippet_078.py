# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_078.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_grid_accepts_primary_axis_presets(tmp_path: Path):

    out_dir = tmp_path / "preview-grid-presets"

    result = run(

        "preview-grid",

        ROBOTO,

        str(out_dir),

        "--axis",

        "wght",

        "--use-presets",

    )

    assert result.returncode == 0

    files = sorted(path.name for path in out_dir.glob("*.png"))

    assert len(files) == 9

    assert "roboto-instance-bold.png" in files