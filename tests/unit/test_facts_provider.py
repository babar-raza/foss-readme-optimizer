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


def _fake_blocked_source_fact(detail: str) -> FactRecordV2:
    return FactRecordV2(
        fact_id="installation.verified_acquisition:blocked-source-build",
        field="installation.verified_acquisition",
        value={
            "method": "source_build",
            "outcome": "BLOCKED_LOCAL_VERIFICATION",
            "detail": detail,
        },
        source=FactSourceV2(
            source_type="mechanical_test",
            location="local-product-verification://acme/widget",
            source_revision="abc123",
        ),
        verification_state="blocked",
        authoritative_owner="repository-owner",
        confidence=0.0,
        affected_surfaces=["readme.overview-navigation-and-acquisition"],
    )


class TestLocalVerificationFactsWithoutProductTruth:
    """policy.product_truth is None -- the exact shape of every real, non-pilot policy
    profile in this repo today (only the 3 Java pilots have product_truth authored)."""

    def test_a_published_package_still_gets_a_registry_verified_acquisition_fact(self, monkeypatch):
        monkeypatch.setattr(
            provider, "collect_acquisition_fact", lambda *a, **k: _fake_registry_fact()
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
        monkeypatch.setattr(
            provider,
            "collect_acquisition_fact",
            lambda *a, **k: _fake_blocked_source_fact(
                "no product_truth.minimal_example configured for this policy profile"
            ),
        )
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
        """A non-.NET repository still needs a governed example source or policy example."""
        monkeypatch.setattr(
            provider,
            "collect_acquisition_fact",
            lambda *a, **k: _fake_blocked_source_fact(
                "no product_truth.minimal_example configured for this policy profile"
            ),
        )
        policy = SimpleNamespace(product_truth=None)

        facts, _ = provider._local_verification_facts(
            "acme/widget", "abc123", None, root=None, policy=policy, entry=None
        )

        assert "example.minimal" not in {f.field for f in facts}


def test_dotnet_repository_example_uses_selected_product_manifest(monkeypatch):
    example = SimpleNamespace(
        language="dotnet",
        class_name="ReadmeExample",
        code="using Aspose.Words;\nvar document = new Document();\n",
        evidence_paths=["examples/quickstart/Program.cs"],
        required_symbols=["Document"],
    )
    verification = _VerifiedRustResult()
    observed_manifests = []
    monkeypatch.setattr(provider, "current_repository_snapshot", lambda _org_repo: object())
    monkeypatch.setattr(provider, "local_fact_verification_allowed", lambda: True)
    monkeypatch.setattr(
        provider,
        "repository_source_example_candidates",
        lambda _root, _language: [example],
    )
    monkeypatch.setattr(
        provider,
        "repository_readme_example_candidates",
        lambda _root, _language: [],
    )

    def select(*_args, requested, verify_example_fn, **_kwargs):
        result = verify_example_fn(requested)
        return SimpleNamespace(outcome="VERIFIED", example=requested, verification=result)

    monkeypatch.setattr(provider, "select_verified_repository_example", select)

    def dotnet_verify(_snapshot, _example, *, selected_product_manifest_path):
        observed_manifests.append(selected_product_manifest_path)
        return verification

    monkeypatch.setattr(provider.dotnet_example_verifier, "verify", dotnet_verify)
    monkeypatch.setattr(
        provider,
        "verify_local_product_example",
        lambda snapshot, selected, *, isolated_verifier=None: isolated_verifier(snapshot, selected),
    )
    monkeypatch.setattr(
        provider,
        "collect_acquisition_fact",
        lambda *_args, **_kwargs: _fake_registry_fact("nuget"),
    )

    facts, local_verification = provider._local_verification_facts(
        "aspose-words-foss/Aspose.Words-FOSS-for-.NET",
        "a" * 40,
        None,
        root=object(),
        policy=SimpleNamespace(product_truth=None),
        entry=SimpleNamespace(ecosystem="net"),
        root_roles=SimpleNamespace(
            selected_product_manifest_path="Aspose.Words/Aspose.Words.csproj"
        ),
    )

    assert observed_manifests == ["Aspose.Words/Aspose.Words.csproj"]
    example_fact = next(fact for fact in facts if fact.field == "example.minimal")
    assert example_fact.verification_state == "verified"
    assert example_fact.fact_id == "example.minimal:compiled-repository-example"
    assert example_fact.value["code"] == example.code
    assert local_verification["outcome"] == "SOURCE_BUILD_VERIFIED"


def test_dotnet_failed_repository_example_preserves_bounded_compiler_diagnostic(monkeypatch):
    example = SimpleNamespace(
        language="dotnet",
        class_name="ReadmeExample",
        code="using Aspose.Email;\n",
        evidence_paths=["examples/Program.cs"],
        required_symbols=["MailMessage"],
    )

    class FailedResult:
        outcome = "BUILD_FAILED"
        detail = "the immutable product source did not compile"
        truth_eligible = False
        build = SimpleNamespace(return_code=1, stderr="error CS1929", stdout="")
        example_compile = None

        def fact_projection(self):
            return {
                "verified_public_symbols": [],
                "input_fixture_bindings": [],
                "public_api_sha256": None,
                "python_package": None,
                "typescript_package": None,
                "rust_package": None,
                "rust_formats": [],
                "rust_source_dependency": None,
                "acquisition_dependency_pins": [],
                "compiled_consumer": None,
            }

        def model_dump(self, *, mode):
            assert mode == "json"
            return {"outcome": self.outcome, "detail": self.detail}

    failed = FailedResult()
    monkeypatch.setattr(provider, "current_repository_snapshot", lambda _org_repo: object())
    monkeypatch.setattr(provider, "local_fact_verification_allowed", lambda: True)
    monkeypatch.setattr(provider, "repository_source_example_candidates", lambda *_args: [example])
    monkeypatch.setattr(provider, "repository_readme_example_candidates", lambda *_args: [])
    monkeypatch.setattr(
        provider,
        "select_verified_repository_example",
        lambda *_args, **_kwargs: SimpleNamespace(
            outcome="NO_VERIFIED_CANDIDATE",
            example=None,
            verification=None,
            last_attempted_example=example,
            last_attempted_verification=failed,
        ),
    )
    monkeypatch.setattr(
        provider,
        "collect_acquisition_fact",
        lambda *_args, **_kwargs: _fake_blocked_source_fact("product source does not compile"),
    )

    facts, verification = provider._local_verification_facts(
        "aspose-email-foss/Aspose.Email-FOSS-for-.NET",
        "a" * 40,
        None,
        root=object(),
        policy=SimpleNamespace(product_truth=None),
        entry=SimpleNamespace(ecosystem="net"),
    )

    example_fact = next(fact for fact in facts if fact.field == "example.minimal")
    assert example_fact.verification_state == "blocked"
    assert "error CS1929" in example_fact.value["verification_detail"]
    assert verification is not None
    assert verification["outcome"] == "BUILD_FAILED"


class _VerifiedRustResult:
    outcome = "SOURCE_BUILD_VERIFIED"
    detail = "locked offline Rust consumer passed"
    truth_eligible = True

    def fact_projection(self):
        return {
            "verified_public_symbols": ["widget::Root", "widget::Root.new"],
            "public_api_sha256": "a" * 64,
            "python_package": None,
            "typescript_package": None,
            "rust_package": {"crate_name": "widget"},
            "rust_formats": [{"format": "xlsx", "direction": "export"}],
            "rust_source_dependency": 'widget = { git = "https://example.invalid", rev = "abc" }',
        }

    def model_dump(self, *, mode):
        assert mode == "json"
        return {"outcome": self.outcome, **self.fact_projection()}


def test_verified_rust_surface_is_preserved_in_example_product_fact(monkeypatch):
    example = SimpleNamespace(
        language="rust",
        class_name="readme_example",
        code="fn main() {}",
        evidence_paths=["src/lib.rs"],
        required_symbols=["widget::Root"],
    )
    policy = SimpleNamespace(product_truth=SimpleNamespace(minimal_example=example))
    monkeypatch.setattr(provider, "current_repository_snapshot", lambda _org_repo: object())
    monkeypatch.setattr(provider, "local_fact_verification_allowed", lambda: True)
    monkeypatch.setattr(provider, "evidence_failures", lambda *_args: [])
    monkeypatch.setattr(
        provider,
        "verify_local_product_example",
        lambda _snapshot, _example: _VerifiedRustResult(),
    )
    monkeypatch.setattr(
        provider,
        "collect_acquisition_fact",
        lambda *_args, **_kwargs: _fake_registry_fact("crates_io"),
    )

    facts, verification = provider._local_verification_facts(
        "acme/widget",
        "abc123",
        "2026-07-27T00:00:00+00:00",
        root=object(),
        policy=policy,
        entry=SimpleNamespace(),
    )

    example_fact = next(fact for fact in facts if fact.field == "example.minimal")
    assert example_fact.verification_state == "verified"
    assert example_fact.value["verified_public_symbols"] == [
        "widget::Root",
        "widget::Root.new",
    ]
    assert example_fact.value["rust_package"] == {"crate_name": "widget"}
    assert example_fact.value["rust_formats"] == [{"format": "xlsx", "direction": "export"}]
    assert verification["outcome"] == "SOURCE_BUILD_VERIFIED"
