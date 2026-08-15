# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_032.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_compute_hash_v5_different_salt(self):

        """Different salts produce different hashes."""

        password = b"password"

        salt1 = b"salt1___"

        salt2 = b"salt2___"

        result1 = EncryptionUtils.compute_hash_v5(password, salt1)

        result2 = EncryptionUtils.compute_hash_v5(password, salt2)

        assert result1 != result2, "Different salts must produce different hashes"