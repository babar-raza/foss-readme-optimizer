# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_027.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_dict_to_bytes_serializes_top_dict_operator():

    d = CffDict()

    d.set(TopDictOp.CHARSTRINGS, [1234])

    out = d.to_bytes()

    parsed = CffDict.from_bytes(out)

    assert parsed.get(TopDictOp.CHARSTRINGS) == [1234]