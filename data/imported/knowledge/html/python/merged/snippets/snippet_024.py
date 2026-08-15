# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_024.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_public_api_doctest():

    import aspose_html.encoding.detection as mod

    results = doctest.testmod(mod, verbose=False)

    assert results.failed == 0, f"{results.failed} doctest(s) failed in detection.py"