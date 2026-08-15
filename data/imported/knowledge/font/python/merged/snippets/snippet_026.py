# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_026.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_dict_to_bytes_roundtrip_preserves_unknown_ops():

    raw = bytes([139, 247, 92, 21, 141, 12, 34])

    d = CffDict.from_bytes(raw)

    out = d.to_bytes()

    parsed = CffDict.from_bytes(out)

    assert parsed.get(21) == [0, 200]

    assert parsed.get((12, 34)) == [2]