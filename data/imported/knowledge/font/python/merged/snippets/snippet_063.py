# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_063.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preview_animation_path_requires_two_states(tmp_path: Path):

    out = tmp_path / "bad-animation-path.png"

    result = run(

        "preview-animation-path",

        ROBOTO,

        str(out),

        "--state",

        "Bold",

    )

    assert result.returncode == 1

    assert "at least two steps" in result.stderr