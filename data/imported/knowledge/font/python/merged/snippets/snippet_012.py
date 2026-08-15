# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_012.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_cff_font_name_nonempty(opensans_cff):

    assert opensans_cff.font_name.strip() != ""