# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_035.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_compute_hash_v5_empty_password(self):

        """Empty password should work without exception."""

        salt = b"12345678"

        result = EncryptionUtils.compute_hash_v5(b"", salt)

        assert len(result) == 32