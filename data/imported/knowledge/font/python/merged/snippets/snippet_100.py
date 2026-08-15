# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_100.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_var_delta_requires_target():

    result = run(

        "var-delta",

        ROBOTO,

        "--instance-name",

        "Bold",

    )

    assert result.returncode == 1

    assert "requires glyph_id or codepoint" in result.stderr