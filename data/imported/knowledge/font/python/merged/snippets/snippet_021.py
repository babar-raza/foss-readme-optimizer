# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_021.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_sid_resolution_standard():

    assert resolve_sid(1, CffIndex([])) == "space"

    assert resolve_sid(228, CffIndex([])) == "zcaron"

    assert resolve_sid(390, CffIndex([])) == "Semibold"