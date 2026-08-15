# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_068.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_accepts_named_instance_plus_override(tmp_path: Path):

    out = tmp_path / "condensed-bold-preview.png"

    result = run(

        "preview",

        ROBOTO,

        str(out),

        "--instance-name",

        "Bold",

        "--instance",

        "wdth=75",

    )

    assert result.returncode == 0

    assert out.exists()

    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")