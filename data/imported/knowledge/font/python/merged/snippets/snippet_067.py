# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_067.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_writes_svg_when_requested(tmp_path: Path):

    out = tmp_path / "bold-preview.svg"

    result = run("preview", ROBOTO, str(out), "--instance-name", "Bold", "--format", "svg")

    assert result.returncode == 0

    assert out.exists()

    data = out.read_bytes()

    assert data.startswith(b'<?xml version="1.0" encoding="UTF-8"?>')

    assert b"<svg " in data

    assert b"<path d=" in data