# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_062.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_animation_path_writes_apng(tmp_path: Path):

    out = tmp_path / "animation-path.png"

    result = run(

        "preview-animation-path",

        ROBOTO,

        str(out),

        "--state",

        "Regular",

        "--state",

        "wght=700,wdth=75",

        "--state",

        "Bold",

        "--frames-per-segment",

        "3",

        "--preset",

        "draft",

        "--easing",

        "ease-in-out",

        "--caption-mode",

        "both",

        "--text",

        "Anim Path",

    )

    assert result.returncode == 0

    assert out.exists()

    data = out.read_bytes()

    assert data.startswith(b"\x89PNG\r\n\x1a\n")

    assert b"acTL" in data