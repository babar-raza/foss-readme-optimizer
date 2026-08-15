# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_006.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_encrypt_decrypt_aes256_roundtrip():

    """Round-trip encryption using 256-bit AES key."""

    key = os.urandom(32)

    plaintext = b"Hello, PDF AES 256!"

    ciphertext = EncryptionUtils.encrypt_aes_cbc(key, plaintext)

    decrypted = EncryptionUtils.decrypt_aes_cbc(key, ciphertext)

    assert decrypted == plaintext