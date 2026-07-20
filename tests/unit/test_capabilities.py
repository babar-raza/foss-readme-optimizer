"""Offline tests for the capability schema, registry, and the capability
wrappers (inspect_repository, detect_readme_gaps, check_install_path from
Wave 2; profile_repository from Wave 3). Mirrors test_validation_rules.py's
scope: the registry and its family of implementations are tested together as
one cohesive unit. No real clone, no real network -- everything the
capabilities call into is monkeypatched."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from readme_agent.capabilities import (
    check_install_path,
    classify_upstream_change,
    detect_readme_gaps,
    domains,
    get_product_facts,
    inspect_repository,
    profile_repository,
    registry,
)
from readme_agent.capabilities.schema import CapabilityGap, CapabilityManifest


def _manifest(**overrides) -> CapabilityManifest:
    defaults = dict(
        capability_id="dummy",
        version="1",
        name="Dummy",
        purpose="test fixture",
        category="test",
        owner="tests",
        execution_type="deterministic_tool",
        required_inputs={"org_repo": "string"},
    )
    return CapabilityManifest(**{**defaults, **overrides})


class TestCapabilityManifestSchema:
    def test_minimal_manifest_is_valid(self):
        m = _manifest()
        assert m.status == "active"
        assert m.side_effect_class == "read_only_local"

    def test_invalid_execution_type_rejected(self):
        with pytest.raises(ValidationError):
            _manifest(execution_type="not_a_real_type")

    def test_invalid_side_effect_class_rejected(self):
        with pytest.raises(ValidationError):
            _manifest(side_effect_class="not_a_real_class")

    def test_allowed_domains_defaults_empty(self):
        m = _manifest()
        assert m.allowed_domains == []

    def test_to_tool_schema_shape(self):
        m = _manifest(
            required_inputs={"org_repo": "string"},
            optional_inputs={"limit": "integer"},
        )
        schema = m.to_tool_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "dummy"
        assert schema["function"]["parameters"]["required"] == ["org_repo"]
        assert set(schema["function"]["parameters"]["properties"]) == {"org_repo", "limit"}


class TestCapabilityGap:
    def test_defaults_are_populated(self):
        gap = CapabilityGap(requested_need="something unsupported", reason="no match")
        assert gap.gap_id
        assert gap.detected_at
        assert gap.requested_capability_id is None


class TestRegistry:
    def test_all_six_capabilities_registered(self):
        ids = {m.capability_id for m in registry.list_all()}
        assert ids == {
            "inspect_repository",
            "detect_readme_gaps",
            "check_install_path",
            "profile_repository",
            "get_product_facts",
            "classify_upstream_change",
        }

    def test_get_returns_manifest(self):
        assert registry.get("inspect_repository") is not None
        assert registry.get("does_not_exist") is None

    def test_get_executor_returns_callable(self):
        assert registry.get_executor("inspect_repository") is inspect_repository.execute
        assert registry.get_executor("does_not_exist") is None

    def test_filter_by_side_effect_class(self):
        network = registry.filter_by(side_effect_class="read_only_network")
        assert [m.capability_id for m in network] == ["check_install_path"]

    def test_filter_by_execution_type(self):
        tools = registry.filter_by(execution_type="deterministic_tool")
        assert len(tools) == 6

    def test_all_tool_schemas_covers_every_capability(self):
        schemas = registry.all_tool_schemas()
        names = {s["function"]["name"] for s in schemas}
        assert names == {
            "inspect_repository",
            "detect_readme_gaps",
            "check_install_path",
            "profile_repository",
            "get_product_facts",
            "classify_upstream_change",
        }

    def test_duplicate_capability_id_raises(self):
        from readme_agent.errors import ConfigError

        dup_module = SimpleNamespace(MANIFEST=_manifest(capability_id="dup"), execute=lambda: {})
        with pytest.raises(ConfigError):
            registry._build((dup_module, dup_module))


class TestRegistryDomainEnforcement:
    """CAP-006/Decision #33 -- the caller-identity axis, orthogonal to
    side_effect_class. Every check here is a no-op against the real registry
    today (domains.KNOWN_DOMAINS is empty), proven by test_capabilities.py's
    own successful collection; these tests exercise the mechanism directly
    against a monkeypatched domain set."""

    def test_unknown_domain_reference_raises(self, monkeypatch):
        from readme_agent.errors import ConfigError

        monkeypatch.setattr(domains, "KNOWN_DOMAINS", frozenset({"readme"}))
        bad_module = SimpleNamespace(
            MANIFEST=_manifest(capability_id="bad", allowed_domains=["metadata"]),
            execute=lambda: {},
        )
        with pytest.raises(ConfigError):
            registry._build((bad_module,))

    def test_known_domain_reference_does_not_raise(self, monkeypatch):
        monkeypatch.setattr(domains, "KNOWN_DOMAINS", frozenset({"readme"}))
        ok_module = SimpleNamespace(
            MANIFEST=_manifest(capability_id="ok", allowed_domains=["readme"]),
            execute=lambda: {},
        )
        registry._build((ok_module,))  # must not raise

    def test_fail_closed_sunset_once_multiple_domains_registered(self, monkeypatch):
        from readme_agent.errors import ConfigError

        monkeypatch.setattr(domains, "KNOWN_DOMAINS", frozenset({"readme", "metadata"}))
        mutating_unscoped = SimpleNamespace(
            MANIFEST=_manifest(
                capability_id="mutator",
                side_effect_class="local_write",
                idempotency_inputs=["org_repo"],
                retry_policy="idempotent_only",
            ),
            execute=lambda: {},
        )
        with pytest.raises(ConfigError):
            registry._build((mutating_unscoped,))

    def test_fail_closed_sunset_does_not_apply_with_only_one_domain_registered(self, monkeypatch):
        monkeypatch.setattr(domains, "KNOWN_DOMAINS", frozenset({"readme"}))
        mutating_unscoped = SimpleNamespace(
            MANIFEST=_manifest(
                capability_id="mutator",
                side_effect_class="local_write",
                idempotency_inputs=["org_repo"],
                retry_policy="idempotent_only",
            ),
            execute=lambda: {},
        )
        registry._build((mutating_unscoped,))  # must not raise -- only one domain registered


class TestRegistryEff001RegistrationGate:
    """Decision #26 addendum -- implements EFF-001's own already-specified
    acceptance criterion: a local_write+ manifest missing idempotency_inputs
    or retry_policy is rejected at registration, before it can ever be
    dispatched."""

    def test_raises_for_mutating_manifest_missing_idempotency(self):
        from readme_agent.errors import ConfigError

        mutator = SimpleNamespace(
            MANIFEST=_manifest(capability_id="mutator", side_effect_class="local_write"),
            execute=lambda: {},
        )
        with pytest.raises(ConfigError):
            registry._build((mutator,))

    def test_does_not_raise_when_idempotency_declared(self):
        mutator = SimpleNamespace(
            MANIFEST=_manifest(
                capability_id="mutator",
                side_effect_class="local_write",
                idempotency_inputs=["org_repo"],
                retry_policy="idempotent_only",
            ),
            execute=lambda: {},
        )
        registry._build((mutator,))  # must not raise

    def test_real_registry_of_six_read_only_capabilities_still_builds_cleanly(self):
        """Regression: all six currently-registered capabilities are
        read-only and must be unaffected by the new mutating-only gate."""
        assert len(registry.list_all()) == 6


class TestInspectRepositoryCapability:
    def test_execute_wraps_inspect_repo(self, monkeypatch):
        monkeypatch.setattr(
            inspect_repository,
            "inspect_repo",
            lambda org_repo, check_install=False: {
                "org_repo": org_repo,
                "manifest": {"artifact_id": "x"},
                "has_readme": True,
                "has_license_file": False,
                "readme_length_chars": 42,
                "presentation_report": None,
            },
        )
        result = inspect_repository.execute("acme/widget")
        assert result == {
            "org_repo": "acme/widget",
            "has_readme": True,
            "has_license_file": False,
            "readme_length_chars": 42,
            "manifest_keys": ["artifact_id"],
        }


class TestDetectReadmeGapsCapability:
    def test_execute_wraps_gap_detector(self, monkeypatch):
        fake_inventory = SimpleNamespace(license_path=None)
        monkeypatch.setattr(
            detect_readme_gaps,
            "_clone_and_scan",
            lambda org_repo: (None, fake_inventory, "# Widget\n\nNo license, no links here."),
        )
        result = detect_readme_gaps.execute("acme/widget")
        flags_only = {k: v for k, v in result.items() if k != "total_gaps"}
        assert result["total_gaps"] == sum(1 for v in flags_only.values() if not v)
        assert set(result) == {
            "license_mentioned",
            "products_org_link",
            "products_com_link",
            "relationship_explained",
            "total_gaps",
        }


class TestCheckInstallPathCapability:
    def test_execute_wraps_presentation_report(self, monkeypatch):
        fake_report = SimpleNamespace(
            install_path_resolved=False,
            evidence={"install_path_resolved": "Maven Central: NOT FOUND (0 results)"},
        )
        monkeypatch.setattr(
            check_install_path,
            "inspect_repo",
            lambda org_repo, check_install=True: {"presentation_report": fake_report},
        )
        result = check_install_path.execute("acme/widget")
        assert result == {
            "install_path_resolved": False,
            "evidence": "Maven Central: NOT FOUND (0 results)",
        }


class TestProfileRepositoryCapability:
    def test_execute_wraps_build_profile(self, monkeypatch, tmp_path):
        from readme_agent.profile.schema import DetectedEcosystem, RepositoryProfile

        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="full")
        fake_profile = RepositoryProfile(
            org_repo="acme/widget",
            detected_ecosystems=[
                DetectedEcosystem(
                    ecosystem="java",
                    manifest_path="pom.xml",
                    confidence=1.0,
                    evidence="found pom.xml; parsed 3 field(s)",
                )
            ],
            unresolved_manifests=[],
        )
        monkeypatch.setattr(profile_repository, "find_entry", lambda org_repo: fake_entry)
        monkeypatch.setattr(profile_repository, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(profile_repository, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(
            profile_repository, "build_profile", lambda org_repo, path: fake_profile
        )

        result = profile_repository.execute("acme/widget")

        assert result["org_repo"] == "acme/widget"
        assert result["detected_ecosystems"][0]["ecosystem"] == "java"
        assert result["unresolved_manifests"] == []

    def test_execute_rejects_disabled_repo(self, monkeypatch):
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="disabled")
        monkeypatch.setattr(profile_repository, "find_entry", lambda org_repo: fake_entry)

        with pytest.raises(PermissionError):
            profile_repository.execute("acme/widget")

    def test_execute_rejects_unknown_repo(self, monkeypatch):
        monkeypatch.setattr(profile_repository, "find_entry", lambda org_repo: None)

        with pytest.raises(PermissionError):
            profile_repository.execute("acme/widget")


class TestGetProductFactsCapability:
    """Wave 6 (decision #37): combines the product inventory + live
    repository profiling, both sources every call, mandatory."""

    def test_execute_combines_both_sources(self, monkeypatch, tmp_path):
        from readme_agent.profile.schema import DetectedEcosystem, RepositoryProfile
        from readme_agent.registry.models import (
            BlockPolicy,
            LicenseElement,
            LinkSpec,
            PolicyProfile,
            RelationshipElement,
            RequiredElements,
            WordLimit,
        )

        fake_entry = SimpleNamespace(
            org="acme",
            repo_name="widget",
            mode="full",
            family="widget",
            platform="java",
            ecosystem="java",
            policy_profile="acme-widget",
        )
        fake_policy = PolicyProfile(
            schema_version=2,
            policy_profile="acme-widget",
            required_elements=RequiredElements(
                license_mentioned=LicenseElement(detected_license="MIT"),
                products_org_link=LinkSpec(
                    url="https://products.acme.org/widget/java/",
                    family_url="https://products.acme.org/widget/",
                    label="Widget",
                ),
                products_com_link=LinkSpec(
                    url="https://products.acme.com/widget/java/",
                    family_url="https://products.acme.com/widget/",
                    label="Widget",
                ),
                relationship_explained=RelationshipElement(
                    min_sentences=2, talking_points=["open_source_scope"]
                ),
            ),
            secondary_links=[],
            block=BlockPolicy(
                word_limit=WordLimit(min=10, max=200),
                prohibited_terms=[],
                link_whitelist_domains=[],
            ),
        )
        fake_profile = RepositoryProfile(
            org_repo="acme/widget",
            detected_ecosystems=[
                DetectedEcosystem(
                    ecosystem="java",
                    manifest_path="pom.xml",
                    confidence=1.0,
                    evidence="found pom.xml",
                )
            ],
            unresolved_manifests=[],
        )
        monkeypatch.setattr(get_product_facts, "find_entry", lambda org_repo: fake_entry)
        monkeypatch.setattr(get_product_facts, "load_policy", lambda profile: fake_policy)
        monkeypatch.setattr(get_product_facts, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(get_product_facts, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(get_product_facts, "build_profile", lambda org_repo, path: fake_profile)

        result = get_product_facts.execute("acme/widget")

        assert result["org_repo"] == "acme/widget"
        assert result["declared_license"] == "MIT"
        assert result["detected_ecosystems"][0]["ecosystem"] == "java"
        assert result["unresolved_manifests"] == []
        assert result["source"]["detected_ecosystems"] == (
            "live repository clone (repository inspection)"
        )

    def test_execute_rejects_disabled_repo(self, monkeypatch):
        fake_entry = SimpleNamespace(mode="disabled")
        monkeypatch.setattr(get_product_facts, "find_entry", lambda org_repo: fake_entry)

        with pytest.raises(PermissionError):
            get_product_facts.execute("acme/widget")

    def test_execute_rejects_unknown_repo(self, monkeypatch):
        monkeypatch.setattr(get_product_facts, "find_entry", lambda org_repo: None)

        with pytest.raises(PermissionError):
            get_product_facts.execute("acme/widget")


class TestClassifyUpstreamChangeCapability:
    """Wave 6 (decision #39): the first capability scoped to a real domain
    (`readme_reconciliation`). Deliberately stateless -- the caller supplies
    the prior fingerprint, the capability never reads/writes durable state."""

    def test_execute_first_observation_when_no_prior_fingerprint(self, monkeypatch, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Widget\n\nSome content.\n", encoding="utf-8")
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="full")
        fake_inventory = SimpleNamespace(readme_path=readme)
        monkeypatch.setattr(classify_upstream_change, "find_entry", lambda org_repo: fake_entry)
        monkeypatch.setattr(classify_upstream_change, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(classify_upstream_change, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(
            classify_upstream_change.file_inventory, "scan", lambda path: fake_inventory
        )
        monkeypatch.setattr(
            classify_upstream_change,
            "get_git_metadata",
            lambda path: SimpleNamespace(commit_sha="abc123"),
        )

        result = classify_upstream_change.execute("acme/widget")

        assert result["classification"] == "FIRST_OBSERVATION"
        assert result["current_revision"] == "abc123"

    def test_execute_no_change_when_fingerprint_matches(self, monkeypatch, tmp_path):
        from readme_agent.readme.facts import sha256_text

        readme_text = "# Widget\n\nSome content.\n"
        readme = tmp_path / "README.md"
        readme.write_text(readme_text, encoding="utf-8")
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="full")
        fake_inventory = SimpleNamespace(readme_path=readme)
        monkeypatch.setattr(classify_upstream_change, "find_entry", lambda org_repo: fake_entry)
        monkeypatch.setattr(classify_upstream_change, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(classify_upstream_change, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(
            classify_upstream_change.file_inventory, "scan", lambda path: fake_inventory
        )
        monkeypatch.setattr(
            classify_upstream_change,
            "get_git_metadata",
            lambda path: SimpleNamespace(commit_sha="abc123"),
        )

        result = classify_upstream_change.execute(
            "acme/widget",
            prior_stripped_text_hash=sha256_text(readme_text),
            prior_owned_span_present=False,
        )

        assert result["classification"] == "NO_CHANGE"

    def test_execute_rejects_disabled_repo(self, monkeypatch):
        fake_entry = SimpleNamespace(mode="disabled")
        monkeypatch.setattr(classify_upstream_change, "find_entry", lambda org_repo: fake_entry)

        with pytest.raises(PermissionError):
            classify_upstream_change.execute("acme/widget")
