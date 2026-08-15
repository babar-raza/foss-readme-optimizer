# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_017.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_verify_password_v4_empty_password(random_file_id):

    """Empty password verification works."""

    o_value = EncryptionUtils.compute_owner_key_v4("owner", "", 16, 4)

    u_value, expected_key = EncryptionUtils.compute_user_key_v4(

        "", o_value, -4, random_file_id, 16, 4

    )



    verified_key = EncryptionUtils.verify_password_v4(

        "", u_value, o_value, -4, random_file_id, 16, 4

    )



    assert verified_key == expected_key, "Empty password verification should work"