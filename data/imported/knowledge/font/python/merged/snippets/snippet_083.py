# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_083.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_compare_invalid_axis_exits_1(tmp_path: Path):

    out = tmp_path / "bad-compare-sheet.png"

    result = run(

        "preview-compare",

        ROBOTO,

        str(out),

        "--after-instance",

        "opsz=12",

    )

    assert result.returncode == 1

    assert "Unknown variable axis" in result.stderr