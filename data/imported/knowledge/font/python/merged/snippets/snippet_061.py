# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_061.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_animation_writes_apng(tmp_path: Path):

    out = tmp_path / "animation.png"

    result = run(

        "preview-animation",

        ROBOTO,

        str(out),

        "--axis",

        "wdth",

        "--start",

        "75",

        "--end",

        "100",

        "--frames",

        "4",

        "--preset",

        "draft",

        "--easing",

        "ease-out",

        "--caption-mode",

        "coordinates",

        "--text",

        "Anim",

    )

    assert result.returncode == 0

    assert out.exists()

    data = out.read_bytes()

    assert data.startswith(b"\x89PNG\r\n\x1a\n")

    assert b"acTL" in data

    assert "Saved:" in result.stdout