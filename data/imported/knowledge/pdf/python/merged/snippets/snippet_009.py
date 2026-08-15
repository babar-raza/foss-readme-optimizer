# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_009.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_compute_owner_key_v4_different_passwords():

    """Different owner passwords produce different O values."""

    o1 = EncryptionUtils.compute_owner_key_v4("owner1", "user", 16, 4)

    o2 = EncryptionUtils.compute_owner_key_v4("owner2", "user", 16, 4)

    assert o1 != o2, "Different passwords should produce different O values"