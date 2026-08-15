# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_020.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_generate_file_id():

    """generate_file_id produces unique 16-byte IDs."""

    id1 = EncryptionUtils.generate_file_id()

    id2 = EncryptionUtils.generate_file_id()



    assert len(id1) == 16

    assert len(id2) == 16

    assert id1 != id2