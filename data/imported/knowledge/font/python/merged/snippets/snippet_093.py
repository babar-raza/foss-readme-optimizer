# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_093.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_var_compat_json_output_file(tmp_path: Path):

    out = tmp_path / "compat.json"

    result = run(

        "var-compat",

        ROBOTO,

        "--before-instance-name",

        "Regular",

        "--after-instance-name",

        "Condensed Bold",

        "--text",

        "Aspose",

        "--json-output",

        str(out),

    )

    assert result.returncode == 0

    assert "Compatible:" in result.stdout

    assert "Saved JSON:" in result.stdout

    payload = json.loads(out.read_text(encoding="utf-8"))

    assert payload["before_label"] == "Regular"

    assert payload["after_label"] == "Condensed Bold"

    assert payload["is_compatible"] is True