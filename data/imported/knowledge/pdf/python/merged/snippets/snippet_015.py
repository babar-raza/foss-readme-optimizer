# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_015.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_verify_password_v4_correct_user_password(random_file_id):

    """Correct user password returns valid encryption key."""

    user_pwd = "testuser"

    o_value = EncryptionUtils.compute_owner_key_v4("owner", user_pwd, 16, 4)

    u_value, expected_key = EncryptionUtils.compute_user_key_v4(

        user_pwd, o_value, -4, random_file_id, 16, 4

    )



    verified_key = EncryptionUtils.verify_password_v4(

        user_pwd, u_value, o_value, -4, random_file_id, 16, 4

    )



    assert verified_key == expected_key, "Correct password should return encryption key"