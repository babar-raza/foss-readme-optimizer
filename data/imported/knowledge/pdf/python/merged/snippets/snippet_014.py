# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_014.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_permissions_affect_derived_key(random_file_id):

    """Different permissions produce different encryption keys."""

    o_value = EncryptionUtils.compute_owner_key_v4("owner", "user", 16, 4)



    _, key1 = EncryptionUtils.compute_user_key_v4(

        "user", o_value, -4, random_file_id, 16, 4

    )

    _, key2 = EncryptionUtils.compute_user_key_v4(

        "user", o_value, -100, random_file_id, 16, 4

    )



    assert key1 != key2, "Different permissions should produce different keys"