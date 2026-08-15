# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_015.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_cff_charset_resolves_gid1(opensans_cff):

    name = opensans_cff.charset.name_for(1)

    assert isinstance(name, str)

    assert name.strip() != ""