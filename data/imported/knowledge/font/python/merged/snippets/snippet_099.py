# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_099.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_var_delta_supports_composite_glyph():

    result = run(

        "var-delta",

        ROBOTO,

        "--instance-name",

        "Bold",

        "--char",

        "Á",

        "--top-points",

        "2",

    )

    assert result.returncode == 0

    assert "Outline support:   composite outline-derived" in result.stdout

    assert "Components:" in result.stdout

    assert "Component motion:" in result.stdout

    assert "GID " in result.stdout

    assert "local=" in result.stdout

    assert "child glyph delta analysis" in result.stdout