# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_020.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_dict_real_encoding():

    # 30 1.5F then operator 21

    d = CffDict.from_bytes(bytes([30, 0x1A, 0x5F, 21]))

    vals = d.get(21)

    assert vals is not None

    assert vals[0] == pytest.approx(1.5)