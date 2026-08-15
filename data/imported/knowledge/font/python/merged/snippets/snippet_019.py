# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_019.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_dict_integer_encoding():

    # 139 -> 0, 140 -> 1, 21 -> operator, thus op 21 has [0, 1]

    d = CffDict.from_bytes(bytes([139, 140, 21]))

    assert d.get(21) == [0, 1]