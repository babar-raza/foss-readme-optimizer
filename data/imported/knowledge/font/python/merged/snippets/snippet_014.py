# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_014.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_cff_charstring_zero_is_bytes(opensans_cff):

    assert isinstance(opensans_cff.charstrings[0], bytes)