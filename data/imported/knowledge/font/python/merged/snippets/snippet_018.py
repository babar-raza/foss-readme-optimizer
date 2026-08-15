# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_018.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_cff_index_empty():

    empty = CffIndex.from_reader(BinaryReader(b"\x00\x00"))

    assert len(empty) == 0