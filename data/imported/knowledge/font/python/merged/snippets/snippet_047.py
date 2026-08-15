# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_047.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_info_rejects_collection_index_for_non_ttc():

    result = run("info", ROBOTO, "--collection-index", "1")

    assert result.returncode == 1

    assert "collection_index is only supported for TTC sources" in result.stderr