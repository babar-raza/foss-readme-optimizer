# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_028.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_cff_standard_strings() -> None:

    strings = cff_standard_strings()

    assert len(strings) == 391

    assert strings[0] == ".notdef"

    assert strings[1] == "space"