# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_073.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_batch_can_write_svg_files(tmp_path: Path):

    out_dir = tmp_path / "preview-batch-svg"

    result = run(

        "preview-batch",

        ROBOTO,

        str(out_dir),

        "--instance-name",

        "Bold",

        "--format",

        "svg",

    )

    assert result.returncode == 0

    files = sorted(path.name for path in out_dir.glob("*.svg"))

    assert files == ["roboto-instance-bold.svg"]

    assert (out_dir / "roboto-instance-bold.svg").read_bytes().startswith(

        b'<?xml version="1.0" encoding="UTF-8"?>'

    )