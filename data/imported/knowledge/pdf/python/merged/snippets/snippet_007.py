# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_007.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_empty_data_aes():

    """AES encryption/decryption works with empty data."""

    key = os.urandom(16)

    plaintext = b""

    ciphertext = EncryptionUtils.encrypt_aes_cbc(key, plaintext)

    decrypted = EncryptionUtils.decrypt_aes_cbc(key, ciphertext)

    assert decrypted == plaintext