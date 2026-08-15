# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_097.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_var_delta_prints_active_tuple_summary():

    result = run(

        "var-delta",

        ROBOTO,

        "--instance-name",

        "Bold",

        "--char",

        "A",

        "--top-points",

        "2",

    )

    assert result.returncode == 0

    assert "Glyph:" in result.stdout

    assert "Instance:" in result.stdout

    assert "Active tuples:" in result.stdout

    assert "Strongest points:" in result.stdout

    assert "outline=" in result.stdout

    assert "phantom=" in result.stdout

    assert "Tuple #" in result.stdout