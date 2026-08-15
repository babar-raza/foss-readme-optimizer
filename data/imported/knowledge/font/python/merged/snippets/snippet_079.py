# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_079.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_grid_sheet_accepts_preset_driven_two_axis_grid(tmp_path: Path):

    out = tmp_path / "grid-sheet-presets.png"

    result = run(

        "preview-grid-sheet",

        ROBOTO,

        str(out),

        "--axis",

        "wght",

        "--use-presets",

        "--axis2",

        "wdth",

        "--use-secondary-presets",

    )

    assert result.returncode == 0

    assert out.exists()

    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")