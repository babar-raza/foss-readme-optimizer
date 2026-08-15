# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_091.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_var_compat_prints_compatibility_summary():

    result = run(

        "var-compat",

        ROBOTO,

        "--before-instance-name",

        "Regular",

        "--after-instance-name",

        "Condensed Bold",

        "--text",

        "Aspose",

    )

    assert result.returncode == 0

    assert "Before:" in result.stdout

    assert "After:" in result.stdout

    assert "Compatible:" in result.stdout

    assert "yes" in result.stdout

    assert "Interpolation diagnostics:" in result.stdout