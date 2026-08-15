# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_033.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_compute_hash_v5_different_password(self):

        """Different passwords produce different hashes."""

        salt = b"12345678"

        result1 = EncryptionUtils.compute_hash_v5(b"pass1", salt)

        result2 = EncryptionUtils.compute_hash_v5(b"pass2", salt)

        assert result1 != result2, "Different passwords must produce different hashes"