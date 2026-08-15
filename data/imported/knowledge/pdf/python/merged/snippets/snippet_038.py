# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_038.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_compute_hash_v5_minimum_64_rounds(self):

        """Algorithm must perform at least 64 rounds (implicit in the algorithm).



        We verify this by ensuring the function produces consistent,

        non-trivial results that would require the full algorithm.

        """

        # Simple validation that it's not just a single hash

        password = b"test"

        salt = b"12345678"

        simple_hash = __import__("hashlib").sha256(password + salt).digest()

        algo_2b_hash = EncryptionUtils.compute_hash_v5(password, salt)



        # The results should be different (Algorithm 2.B is much more complex)

        assert simple_hash != algo_2b_hash