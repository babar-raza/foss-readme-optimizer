# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_011.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_override_invalid_label():

    with pytest.raises(ValueError):

        detect_encoding(b"<p>hello</p>", override_encoding="not-real")