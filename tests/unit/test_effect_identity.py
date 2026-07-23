"""`EFF-006` (Wave 9.6): `EffectIdentityV1`/`build_effect_identity()` in
isolation -- `test_effect_ledger.py::TestCandidateAwareIdempotencyKey`/
`TestDispatchGatedEffectCandidateAwareness` prove this is actually wired
into `idempotency_key()`."""

from readme_agent.capabilities.effect_identity import (
    EffectIdentityV1,
    build_effect_identity,
    compute_candidate_byte_hash,
)


class TestComputeCandidateByteHash:
    def test_different_text_different_hash(self):
        assert compute_candidate_byte_hash("# A\n") != compute_candidate_byte_hash("# B\n")

    def test_identical_text_identical_hash(self):
        assert compute_candidate_byte_hash("# A\n") == compute_candidate_byte_hash("# A\n")


class TestBuildEffectIdentity:
    def test_populates_all_fields_from_the_given_inputs(self):
        identity = build_effect_identity(
            effect_type="commit_readme_write",
            org_repo="acme/widget",
            facts_hash="factsabc",
            fresh_fingerprint="freshdef",
            final_text="# Widget\n",
        )
        assert identity == EffectIdentityV1(
            effect_type="commit_readme_write",
            org_repo="acme/widget",
            upstream_surface_hash="freshdef",
            candidate_byte_hash=compute_candidate_byte_hash("# Widget\n"),
            product_facts_hash="factsabc",
        )

    def test_differing_final_text_produces_differing_candidate_byte_hash_only(self):
        base = dict(
            effect_type="commit_readme_write",
            org_repo="acme/widget",
            facts_hash="factsabc",
            fresh_fingerprint="freshdef",
        )
        first = build_effect_identity(**base, final_text="# Widget v1\n")
        second = build_effect_identity(**base, final_text="# Widget v2\n")
        assert first.candidate_byte_hash != second.candidate_byte_hash
        assert first.upstream_surface_hash == second.upstream_surface_hash
        assert first.product_facts_hash == second.product_facts_hash


class TestCanonicalJson:
    def test_deterministic_across_equal_instances(self):
        identity = build_effect_identity(
            effect_type="open_presentation_pr",
            org_repo="acme/widget",
            facts_hash="factsabc",
            fresh_fingerprint="freshdef",
            final_text="# Widget\n",
        )
        same = EffectIdentityV1(**identity.model_dump())
        assert identity.canonical_json() == same.canonical_json()

    def test_differs_when_any_field_differs(self):
        identity = build_effect_identity(
            effect_type="open_presentation_pr",
            org_repo="acme/widget",
            facts_hash="factsabc",
            fresh_fingerprint="freshdef",
            final_text="# Widget\n",
        )
        other = build_effect_identity(
            effect_type="open_presentation_pr",
            org_repo="acme/widget",
            facts_hash="factsabc",
            fresh_fingerprint="freshdef",
            final_text="# Widget, revised\n",
        )
        assert identity.canonical_json() != other.canonical_json()
