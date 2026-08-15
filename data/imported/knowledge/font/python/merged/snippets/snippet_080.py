# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_080.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_grid_sheet_writes_composite_png(tmp_path: Path):

    out = tmp_path / "grid-sheet.png"

    result = run(

        "preview-grid-sheet",

        ROBOTO,

        str(out),

        "--axis",

        "wght",

        "--value",

        "400",

        "--value",

        "700",

        "--axis2",

        "wdth",

        "--value2",

        "75",

        "--value2",

        "100",

    )

    assert result.returncode == 0

    assert out.exists()

    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    assert "Saved:" in result.stdout