# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_081.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_compare_writes_comparison_png(tmp_path: Path):

    out = tmp_path / "compare-sheet.png"

    result = run(

        "preview-compare",

        ROBOTO,

        str(out),

        "--before-instance-name",

        "Regular",

        "--after-instance-name",

        "Condensed Bold",

    )

    assert result.returncode == 0

    assert out.exists()

    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    assert "Saved:" in result.stdout