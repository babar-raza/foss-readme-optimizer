# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_015.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_label_whitespace():

    assert get_canonical_name("  windows-1252  ") == "windows-1252"