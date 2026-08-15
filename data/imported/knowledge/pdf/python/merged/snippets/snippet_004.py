# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_004.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_invalid_key_length_raises():

    """EncryptionUtils should reject invalid AES key lengths."""

    with pytest.raises(Exception, match="AES key must be 16, 24, or 32 bytes"):

        EncryptionUtils.encrypt_aes_cbc(b"short", b"data")

    with pytest.raises(Exception, match="AES key must be 16, 24, or 32 bytes"):

        EncryptionUtils.decrypt_aes_cbc(b"short", b"X" * 20)