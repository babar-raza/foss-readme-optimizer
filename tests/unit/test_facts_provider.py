"""Focused tests for facts/provider.py::_local_verification_facts -- specifically the
2026-07-25 fix (found running the Level-5 portfolio-wide local-proposal pipeline): package-
acquisition verification must never be skipped just because a repo's policy has no
`product_truth.minimal_example` authored yet. Every non-pilot registry entry (28 of 31)
was silently getting NO `installation.verified_acquisition` fact at all before this fix."""

from types import SimpleNamespace

from readme_agent.facts import provider
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2


def _fake_source() -> FactSourceV2:
    return FactSourceV2(
        source_type="external_registry",
        location="registry-acquisition://python",
        source_revision="abc123",
        retrieved_at=None,
    )


def _fake_registry_fact(method: str = "pypi") -> FactRecordV2:
    return FactRecordV2(
        fact_id="installation.verified_acquisition:registry-pypi",
        field="installation.verified_acquisition",
        value={
            "method": method,
            "outcome": "REGISTRY_VERIFIED",
            "detail": "found",
            "coordinate": {},
        },
        source=_fake_source(),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme.overview-navigation-and-acquisition"],
    )


class TestLocalVerificationFactsWithoutProductTruth:
    """policy.product_truth is None -- the exact shape of every real, non-pilot policy
    profile in this repo today (only the 3 Java pilots have product_truth authored)."""

    def test_a_published_package_still_gets_a_registry_verified_acquisition_fact(self, monkeypatch):
        monkeypatch.setattr(
            provider, "_registry_acquisition_fact", lambda *a, **k: _fake_registry_fact()
        )
        policy = SimpleNamespace(product_truth=None)

        facts, local_verification = provider._local_verification_facts(
            "acme/widget", "abc123", None, root=None, policy=policy, entry=None
        )

        fields = {f.field for f in facts}
        assert fields == {"installation.verified_acquisition"}
        assert local_verification is None

        acquisition = next(f for f in facts if f.field == "installation.verified_acquisition")
        assert acquisition.value["method"] == "pypi"
        assert acquisition.value["outcome"] == "REGISTRY_VERIFIED"
        assert acquisition.verification_state == "verified"

    def test_an_unpublished_package_gets_an_honest_source_build_fact_not_a_missing_one(
        self, monkeypatch
    ):
        """The bug this fix closes: before it, this scenario produced NO fact at all for
        installation.verified_acquisition -- resolve_product_facts() then filled it with
        its own value=None placeholder, which the independent verifier correctly (but
        confusingly) reported as 'method=None -- an unpublished package cannot be
        verified' instead of the honest, complete source_build record this restores."""
        monkeypatch.setattr(provider, "_registry_acquisition_fact", lambda *a, **k: None)
        policy = SimpleNamespace(product_truth=None)

        facts, local_verification = provider._local_verification_facts(
            "acme/widget", "abc123", None, root=None, policy=policy, entry=None
        )

        fields = {f.field for f in facts}
        assert fields == {"installation.verified_acquisition"}
        assert local_verification is None

        acquisition = next(f for f in facts if f.field == "installation.verified_acquisition")
        assert acquisition.value["method"] == "source_build"
        assert acquisition.value["outcome"] == "BLOCKED_LOCAL_VERIFICATION"
        assert "no product_truth.minimal_example configured" in acquisition.value["detail"]
        # Honestly blocked (nothing was compiled), never falsely "verified".
        assert acquisition.verification_state == "blocked"
        assert acquisition.confidence == 0.0

    def test_no_example_minimal_fact_is_produced_without_product_truth(self, monkeypatch):
        """Correct, not a regression: there is genuinely no example to compile without a
        policy-authored minimal_example -- only the acquisition fact is restored by this
        fix, example.minimal legitimately stays absent (and resolve_product_facts() will
        mark it 'missing', an honest reflection of reality)."""
        monkeypatch.setattr(provider, "_registry_acquisition_fact", lambda *a, **k: None)
        policy = SimpleNamespace(product_truth=None)

        facts, _ = provider._local_verification_facts(
            "acme/widget", "abc123", None, root=None, policy=policy, entry=None
        )

        assert "example.minimal" not in {f.field for f in facts}
