# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_094.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_var_compat_json_stdout_and_output_file(tmp_path: Path):

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

        "--json",

        "--json-output",

        str(out),

    )

    assert result.returncode == 0

    payload = json.loads(result.stdout)

    assert payload["is_compatible"] is True

    assert "Saved JSON:" not in result.stdout

    file_payload = json.loads(out.read_text(encoding="utf-8"))

    assert file_payload == payload