# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_010.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_compute_owner_key_v4_empty_owner_uses_user():

    """Empty owner password defaults to user password."""

    o1 = EncryptionUtils.compute_owner_key_v4("", "user", 16, 4)

    o2 = EncryptionUtils.compute_owner_key_v4("user", "user", 16, 4)

    assert o1 == o2, "Empty owner password should use user password"