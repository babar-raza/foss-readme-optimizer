"""Offline tests for the capability schema, registry, and the capability
wrappers (inspect_repository, detect_readme_gaps, check_install_path from
Wave 2; profile_repository from Wave 3). Mirrors test_validation_rules.py's
scope: the registry and its family of implementations are tested together as
one cohesive unit. No real clone, no real network -- everything the
capabilities call into is monkeypatched."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from readme_agent.capabilities import (
    audit_community_files,
    audit_github_generated_surfaces,
    audit_package_release_surfaces,
    check_install_path,
    classify_upstream_change,
    commit_readme_write,
    compare_against_presentation_standard,
    compare_reference_repositories,
    detect_readme_gaps,
    domains,
    get_domain_findings,
    get_product_facts,
    get_template_clone_findings,
    inspect_repository,
    prepare_visual_asset,
    profile_repository,
    propose_metadata_changes,
    registry,
    render_readme_candidate,
    review_visual_asset_accuracy,
    stop,
    verify_prose_quality,
    verify_readme_candidate,
)
from readme_agent.capabilities.schema import (
    CapabilityGap,
    CapabilityManifest,
    OrgRepoOnlyInputV1,
)
from readme_agent.errors import NotAllowlistedError
from readme_agent.facts import provider as facts_provider
from readme_agent.facts.migration import migrate_product_facts_v1
from readme_agent.facts.schema import ProductFactsV1
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.profile.schema import DetectedEcosystem, RepositoryProfile
from readme_agent.state.schema import DomainStateV1, RunStateV1


def _manifest(**overrides) -> CapabilityManifest:
    side_effect_class = overrides.get("side_effect_class", "read_only_local")
    defaults = dict(
        capability_id="dummy",
        version="1",
        name="Dummy",
        purpose="test fixture",
        category="test",
        owner="tests",
        execution_type="deterministic_tool",
        required_inputs={"org_repo": "string"},
        produced_outputs={"ok": "boolean"},
        required_permissions=[side_effect_class],
        evidence_outputs=["ok"] if side_effect_class in {"local_write", "remote_write"} else [],
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

    def test_to_tool_schema_prefers_input_model_when_declared(self):
        """Wave 11.4 (`CAP-008`): a manifest with `input_model` set uses
        its real `model_json_schema()`, not the flat type-name map -- even
        when `required_inputs` is also (redundantly) populated."""
        m = _manifest(input_model=OrgRepoOnlyInputV1)
        schema = m.to_tool_schema()
        assert schema["function"]["parameters"]["required"] == ["org_repo"]
        assert set(schema["function"]["parameters"]["properties"]) == {"org_repo"}

    def test_to_tool_schema_strips_the_input_models_own_docstring_description(self):
        """The generated schema's own `description` (Pydantic's default:
        the model's docstring) must never leak into the LLM-facing schema
        -- `function.description` (from `purpose`) is the one authoritative
        description."""
        m = _manifest(input_model=OrgRepoOnlyInputV1, purpose="the real purpose text")
        schema = m.to_tool_schema()
        assert schema["function"]["description"] == "the real purpose text"
        assert "description" not in schema["function"]["parameters"]

    def test_input_model_defaults_to_none(self):
        assert _manifest().input_model is None
        assert _manifest().output_model is None

    def test_effect_classes_defaults_empty(self):
        assert _manifest().effect_classes == []


class TestOrgRepoRef:
    """Wave 11.4 (`CAP-008`): the concrete "reject invalid repo refs"
    validator -- proven both standalone and through the shared
    `OrgRepoOnlyInputV1` input model three real capabilities now use."""

    def test_valid_org_repo_passes(self):
        model = OrgRepoOnlyInputV1(org_repo="acme/widget")
        assert model.org_repo == "acme/widget"

    def test_missing_slash_is_rejected(self):
        with pytest.raises(ValidationError):
            OrgRepoOnlyInputV1(org_repo="acme-widget")

    def test_empty_string_is_rejected(self):
        with pytest.raises(ValidationError):
            OrgRepoOnlyInputV1(org_repo="")

    def test_extra_path_segment_is_rejected(self):
        with pytest.raises(ValidationError):
            OrgRepoOnlyInputV1(org_repo="acme/widget/extra")

    def test_dots_hyphens_and_underscores_are_permitted(self):
        model = OrgRepoOnlyInputV1(org_repo="acme-org/widget_v2.foss")
        assert model.org_repo == "acme-org/widget_v2.foss"

    def test_error_message_names_the_offending_value(self):
        with pytest.raises(ValidationError) as exc_info:
            OrgRepoOnlyInputV1(org_repo="no-slash-here")
        assert "no-slash-here" in str(exc_info.value)


class TestCapabilityGap:
    def test_defaults_are_populated(self):
        gap = CapabilityGap(requested_need="something unsupported", reason="no match")
        assert gap.gap_id
        assert gap.detected_at
        assert gap.requested_capability_id is None


class TestRegistry:
    def test_all_twenty_two_capabilities_registered(self):
        ids = {m.capability_id for m in registry.list_all()}
        assert ids == {
            "inspect_repository",
            "detect_readme_gaps",
            "check_install_path",
            "profile_repository",
            "get_product_facts",
            "classify_upstream_change",
            "render_readme_candidate",
            "audit_github_generated_surfaces",
            "audit_package_release_surfaces",
            "propose_metadata_changes",
            "audit_community_files",
            "commit_readme_write",
            # TC-08: the one real remote-write capability.
            "open_presentation_pr",
            "prepare_visual_asset",
            "verify_readme_candidate",
            # Wave 8.5 (AGT-008): on-demand full-detail drill-down for the
            # supervisor's per-turn dossier summaries.
            "get_domain_findings",
            # Wave 8.6 (VER-006 reversal): additive prose-quality check.
            "verify_prose_quality",
            # Wave 8.6 (comparison capabilities): ongoing runtime comparison
            # against the codified presentation standard, plus the periodic
            # reference-repository re-fetch.
            "compare_against_presentation_standard",
            "compare_reference_repositories",
            # Wave 8.6 (item H): vision-model accuracy review, advisory only.
            "review_visual_asset_accuracy",
            # Wave 8.6 (item I): periodic embedding-similarity findings drill-down.
            "get_template_clone_findings",
            # TC-17 (decision #46, AGT-006): the real, registered stop capability.
            "stop",
            # Wave 11.2 (PKG-005): per-package-root live acquisition verification.
            "verify_package_acquisition",
        }

    def test_get_returns_manifest(self):
        assert registry.get("inspect_repository") is not None
        assert registry.get("does_not_exist") is None

    def test_every_registered_capability_has_typed_input_and_output_models(self):
        manifests = registry.list_all()
        assert manifests
        assert all(manifest.input_model is not None for manifest in manifests)
        assert all(manifest.output_model is not None for manifest in manifests)

    def test_manifest_missing_its_side_effect_permission_is_rejected(self):
        from readme_agent.errors import ConfigError

        module = SimpleNamespace(
            MANIFEST=_manifest(required_permissions=[]),
            execute=lambda: {},
        )
        with pytest.raises(ConfigError, match="required_permissions"):
            registry._build((module,))

    def test_unknown_validator_is_rejected(self):
        from readme_agent.errors import ConfigError

        module = SimpleNamespace(
            MANIFEST=_manifest(validators=["not_a_registered_rule"]),
            execute=lambda: {},
        )
        with pytest.raises(ConfigError, match="unknown validators"):
            registry._build((module,))

    def test_mutating_manifest_without_evidence_outputs_is_rejected(self):
        from readme_agent.errors import ConfigError

        module = SimpleNamespace(
            MANIFEST=_manifest(
                side_effect_class="local_write",
                evidence_outputs=[],
                idempotency_inputs=["org_repo"],
                retry_policy="idempotent_only",
                allowed_domains=["readme_reconciliation"],
            ),
            execute=lambda: {},
        )
        with pytest.raises(ConfigError, match="no evidence_outputs"):
            registry._build((module,))

    def test_evidence_output_must_exist_in_output_contract(self):
        from readme_agent.errors import ConfigError

        module = SimpleNamespace(
            MANIFEST=_manifest(evidence_outputs=["missing"]),
            execute=lambda: {},
        )
        with pytest.raises(ConfigError, match="output contract"):
            registry._build((module,))

    def test_unknown_profile_compatibility_vocabulary_is_rejected(self):
        from readme_agent.errors import ConfigError

        module = SimpleNamespace(
            MANIFEST=_manifest(supported_build_systems=["invented_build"]),
            execute=lambda: {},
        )
        with pytest.raises(ConfigError, match="unknown supported_build_systems"):
            registry._build((module,))

    def test_repository_profile_compatibility_filter_is_data_driven(self):
        java_profile = RepositoryProfile(
            org_repo="acme/widget",
            detected_ecosystems=[
                DetectedEcosystem(
                    ecosystem="java",
                    manifest_path="pom.xml",
                    confidence=1.0,
                    evidence="test",
                )
            ],
        )
        cpp_profile = RepositoryProfile(
            org_repo="acme/widget",
            detected_ecosystems=[
                DetectedEcosystem(
                    ecosystem="cpp",
                    manifest_path="CMakeLists.txt",
                    confidence=1.0,
                    evidence="test",
                )
            ],
        )

        java_ids = {manifest.capability_id for manifest in registry.filter_compatible(java_profile)}
        cpp_ids = {manifest.capability_id for manifest in registry.filter_compatible(cpp_profile)}

        assert "check_install_path" in java_ids
        assert "verify_package_acquisition" in java_ids
        assert "check_install_path" not in cpp_ids
        assert "verify_package_acquisition" not in cpp_ids
        assert "inspect_repository" in java_ids & cpp_ids

    def test_get_executor_returns_callable(self):
        assert registry.get_executor("inspect_repository") is inspect_repository.execute
        assert registry.get_executor("does_not_exist") is None

    def test_filter_by_side_effect_class(self):
        network = registry.filter_by(side_effect_class="read_only_network")
        assert {m.capability_id for m in network} == {
            "check_install_path",
            "audit_github_generated_surfaces",
            "audit_package_release_surfaces",
            "propose_metadata_changes",
            "audit_community_files",
            "get_domain_findings",
            "verify_prose_quality",
            "compare_against_presentation_standard",
            "compare_reference_repositories",
            "review_visual_asset_accuracy",
            "verify_package_acquisition",
        }

    def test_filter_by_side_effect_class_local_write(self):
        """Wave 7g: the first (and, this wave, only) real mutating capability."""
        mutating = registry.filter_by(side_effect_class="local_write")
        assert {m.capability_id for m in mutating} == {"commit_readme_write"}

    def test_filter_by_side_effect_class_remote_write(self):
        """TC-08: the first (and, this wave, only) real remote-write capability."""
        mutating = registry.filter_by(side_effect_class="remote_write")
        assert {m.capability_id for m in mutating} == {"open_presentation_pr"}

    def test_filter_by_execution_type(self):
        tools = registry.filter_by(execution_type="deterministic_tool")
        assert len(tools) == 11  # Wave 11.2 adds "verify_package_acquisition"

    def test_filter_by_execution_type_manual_delivery_preparation(self):
        """Wave 7h: the first capability to use this execution_type,
        declared in schema.py since the Wave 2 sprint but unused until now."""
        prepared = registry.filter_by(execution_type="manual_delivery_preparation")
        assert {m.capability_id for m in prepared} == {"prepare_visual_asset"}

    def test_all_tool_schemas_with_no_caller_domain_excludes_domain_scoped_capabilities(self):
        """Wave 7 fix: the general (unscoped) planner must never be offered
        a capability it can only get `rejected_domain_denied` for --
        `classify_upstream_change` is scoped to `readme_reconciliation` and
        is correctly excluded from the default, caller_domain=None view."""
        schemas = registry.all_tool_schemas()
        names = {s["function"]["name"] for s in schemas}
        assert names == {
            "inspect_repository",
            "detect_readme_gaps",
            "check_install_path",
            "profile_repository",
            "get_product_facts",
            "render_readme_candidate",
            # Wave 8.5 (AGT-008): unscoped, general-planner-visible on-demand
            # drill-down capability.
            "get_domain_findings",
            # Wave 8.6 (item I): unscoped, general-planner-visible drill-down.
            "get_template_clone_findings",
            # TC-17 (decision #46, AGT-006): unscoped, general-planner-visible.
            "stop",
            # Wave 11.2 (PKG-005): unscoped, general-planner-visible.
            "verify_package_acquisition",
        }
        assert "classify_upstream_change" not in names
        # The one real mutating capability must never be offered to the
        # general planner either -- domain-scoped to readme_presentation.
        assert "commit_readme_write" not in names
        assert "prepare_visual_asset" not in names
        # Wave 8b: the independent verifier is scoped to independent_verification.
        assert "verify_readme_candidate" not in names
        # Wave 8.6 (VER-006 reversal): also independent_verification-scoped.
        assert "verify_prose_quality" not in names

    def test_all_tool_schemas_with_matching_caller_domain_includes_scoped_capability(self):
        from readme_agent.capabilities.domains import README_RECONCILIATION

        schemas = registry.all_tool_schemas(caller_domain=README_RECONCILIATION)
        names = {s["function"]["name"] for s in schemas}
        assert "classify_upstream_change" in names
        # Unscoped capabilities remain visible to every caller domain too.
        assert "inspect_repository" in names

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


class TestRegistryEffectClassEnforcement:
    """Wave 13.3 (`AUTH-004`): the same build-time membership check pattern
    `TestRegistryDomainEnforcement` above already established, for the
    separate `effect_classes` axis (`authorization.schema.EffectClass`)."""

    def test_unknown_effect_class_raises(self):
        from readme_agent.errors import ConfigError

        bad_module = SimpleNamespace(
            MANIFEST=_manifest(capability_id="bad", effect_classes=["NOT_A_REAL_CLASS"]),
            execute=lambda: {},
        )
        with pytest.raises(ConfigError):
            registry._build((bad_module,))

    def test_known_effect_class_does_not_raise(self):
        ok_module = SimpleNamespace(
            MANIFEST=_manifest(capability_id="ok", effect_classes=["PR_BRANCH_PUSH"]),
            execute=lambda: {},
        )
        registry._build((ok_module,))  # must not raise

    def test_the_real_open_presentation_pr_capability_declares_its_effect_classes(self):
        manifest = registry.get("open_presentation_pr")
        assert manifest.effect_classes == ["PR_BRANCH_PUSH", "PR_CREATE_OR_UPDATE"]

    def test_the_real_commit_readme_write_capability_declares_no_effect_classes(self):
        """Deliberate (see `commit_readme_write.py`'s own docstring) -- a
        local-only, never-pushed commit has no external blast radius any
        `EffectClass` value actually describes."""
        manifest = registry.get("commit_readme_write")
        assert manifest.effect_classes == []


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
                # Real domains.KNOWN_DOMAINS now has 2 entries (Wave 7b) --
                # scope to a real one so the fail-closed sunset (a separate
                # gate, covered by TestRegistryDomainEnforcement) doesn't
                # also trip here; this test is only about the idempotency gate.
                allowed_domains=["readme_reconciliation"],
            ),
            execute=lambda: {},
        )
        registry._build((mutator,))  # must not raise

    def test_real_registry_of_twenty_two_capabilities_still_builds_cleanly(self):
        """Regression: twenty-one read-only capabilities plus the two real
        mutating capabilities (commit_readme_write, Wave 7g;
        open_presentation_pr, TC-08) all pass the mutating-only gate."""
        assert len(registry.list_all()) == 23


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
        monkeypatch.setattr(profile_repository, "require_listed", lambda org_repo: fake_entry)
        monkeypatch.setattr(
            profile_repository, "get_or_build_profile", lambda entry, **kwargs: fake_profile
        )

        result = profile_repository.execute("acme/widget")

        assert result["org_repo"] == "acme/widget"
        assert result["detected_ecosystems"][0]["ecosystem"] == "java"
        assert result["unresolved_manifests"] == []

    def test_execute_allows_disabled_repo(self, monkeypatch, tmp_path):
        """Decision #40: mode == "disabled" means push access is unverified,
        not "excluded from analysis" -- this read-only capability runs
        against every registered repo regardless of mode."""
        from readme_agent.profile.schema import RepositoryProfile

        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="disabled")
        fake_profile = RepositoryProfile(
            org_repo="acme/widget", detected_ecosystems=[], unresolved_manifests=[]
        )
        monkeypatch.setattr(profile_repository, "require_listed", lambda org_repo: fake_entry)
        monkeypatch.setattr(
            profile_repository, "get_or_build_profile", lambda entry, **kwargs: fake_profile
        )

        result = profile_repository.execute("acme/widget")

        assert result["org_repo"] == "acme/widget"

    def test_execute_rejects_unknown_repo(self, monkeypatch):
        def _raise(org_repo):
            raise NotAllowlistedError(f"{org_repo} is not in data/products.json")

        monkeypatch.setattr(profile_repository, "require_listed", _raise)

        with pytest.raises(NotAllowlistedError):
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
        monkeypatch.setattr(facts_provider, "require_listed", lambda org_repo: fake_entry)
        monkeypatch.setattr(facts_provider, "load_policy", lambda profile: fake_policy)
        monkeypatch.setattr(
            facts_provider, "get_or_build_profile", lambda entry, **kwargs: fake_profile
        )

        result = get_product_facts.execute("acme/widget")

        assert result["org_repo"] == "acme/widget"
        assert result["declared_license"] == "MIT"
        assert result["detected_ecosystems"][0]["ecosystem"] == "java"
        assert result["unresolved_manifests"] == []
        assert result["source"]["detected_ecosystems"] == (
            "live repository clone (repository inspection)"
        )
        assert result["surface_ownership"]["schema_version"] == 1
        assert result["product_facts_v2"]["schema_version"] == 2
        assert "product.identity" in result["product_facts_v2"]["selected_fact_ids"]
        limitations_id = result["product_facts_v2"]["selected_fact_ids"]["product.limitations"]
        limitations = next(
            fact
            for fact in result["product_facts_v2"]["facts"]
            if fact["fact_id"] == limitations_id
        )
        assert limitations["verification_state"] == "missing"

    def test_execute_exposes_package_roots(self, monkeypatch, tmp_path):
        """Wave 11.3 (`FACT-010`): additive -- `package_roots` was already
        computed inside `profile` (Wave 11.1) but never exposed here."""
        from readme_agent.profile.schema import PackageRoot, RepositoryProfile
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
            package_roots=[
                PackageRoot(
                    path=".",
                    ecosystem="java",
                    manifest_path="pom.xml",
                    confidence=1.0,
                    evidence="found pom.xml",
                )
            ],
        )
        monkeypatch.setattr(facts_provider, "require_listed", lambda org_repo: fake_entry)
        monkeypatch.setattr(facts_provider, "load_policy", lambda profile: fake_policy)
        monkeypatch.setattr(
            facts_provider, "get_or_build_profile", lambda entry, **kwargs: fake_profile
        )

        result = get_product_facts.execute("acme/widget")

        assert result["package_roots"] == [
            {
                "path": ".",
                "ecosystem": "java",
                "manifest_path": "pom.xml",
                "confidence": 1.0,
                "evidence": "found pom.xml",
            }
        ]
        assert result["source"]["package_roots"] == "live repository clone (repository inspection)"

    def test_execute_allows_disabled_repo(self, monkeypatch, tmp_path):
        """Decision #40: mode == "disabled" means push access is unverified,
        not "excluded from analysis" -- this read-only capability runs
        against every registered repo regardless of mode."""
        from readme_agent.profile.schema import RepositoryProfile
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
            mode="disabled",
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
            org_repo="acme/widget", detected_ecosystems=[], unresolved_manifests=[]
        )
        monkeypatch.setattr(facts_provider, "require_listed", lambda org_repo: fake_entry)
        monkeypatch.setattr(facts_provider, "load_policy", lambda profile: fake_policy)
        monkeypatch.setattr(
            facts_provider, "get_or_build_profile", lambda entry, **kwargs: fake_profile
        )

        result = get_product_facts.execute("acme/widget")

        assert result["org_repo"] == "acme/widget"

    def test_execute_rejects_unknown_repo(self, monkeypatch):
        def _raise(org_repo):
            raise NotAllowlistedError(f"{org_repo} is not in data/products.json")

        monkeypatch.setattr(facts_provider, "require_listed", _raise)

        with pytest.raises(NotAllowlistedError):
            get_product_facts.execute("acme/widget")

    def test_execute_raises_when_policy_profile_missing(self, monkeypatch):
        """Wave 8.7 drive-by: this branch was previously untested entirely
        and raised a bare ValueError -- harmonized to NotAllowlistedError to
        match the other two "not onboarded" raise sites."""
        fake_entry = SimpleNamespace(
            org="acme",
            repo_name="widget",
            mode="dry_run",
            family="widget",
            platform="java",
            ecosystem="java",
            policy_profile=None,
        )
        monkeypatch.setattr(facts_provider, "require_listed", lambda org_repo: fake_entry)

        with pytest.raises(NotAllowlistedError):
            get_product_facts.execute("acme/widget")


class TestRenderReadmeCandidateCapability:
    """Wave 7 `EFF-001` fix: the read-only half of the render/commit split.
    `execute()` must shape `prepare_readme_candidate()`'s full `ReadmeCandidate`
    into exactly the JSON-serializable subset `commit_readme_write` and the
    `readme_presentation` specialist need -- nothing more, nothing dropped."""

    def test_execute_wraps_prepare_readme_candidate(self, monkeypatch):
        fake_candidate = SimpleNamespace(
            facts_hash="deadbeef",
            fresh_fingerprint="cafef00d",
            skip_regeneration=False,
            original_text="# Widget\n",
            final_text="# Widget\n\n<!-- resources -->\n",
            status="GENERATED",
            llm_called=True,
            llm_calls=["relationship_explained"],
        )
        monkeypatch.setattr(
            render_readme_candidate,
            "prepare_readme_candidate",
            lambda org_repo, **kwargs: fake_candidate,
        )
        result = render_readme_candidate.execute("acme/widget")
        assert result == {
            "facts_hash": "deadbeef",
            "fresh_fingerprint": "cafef00d",
            "skip_regeneration": False,
            "needs_write": True,
            "original_text": "# Widget\n",
            "final_text": "# Widget\n\n<!-- resources -->\n",
            "status": "GENERATED",
            "llm_called": True,
            "llm_calls": ["relationship_explained"],
        }

    def test_execute_needs_write_false_when_final_text_unchanged(self, monkeypatch):
        fake_candidate = SimpleNamespace(
            facts_hash="deadbeef",
            fresh_fingerprint="cafef00d",
            skip_regeneration=True,
            original_text="# Widget\n",
            final_text="# Widget\n",
            status="COMPLIANT_NO_CHANGE",
            llm_called=False,
            llm_calls=[],
        )
        monkeypatch.setattr(
            render_readme_candidate,
            "prepare_readme_candidate",
            lambda org_repo, **kwargs: fake_candidate,
        )
        result = render_readme_candidate.execute("acme/widget")
        assert result["needs_write"] is False
        assert result["status"] == "COMPLIANT_NO_CHANGE"

    def test_manifest_is_unscoped_read_only(self):
        assert render_readme_candidate.MANIFEST.side_effect_class == "read_only_local"
        assert render_readme_candidate.MANIFEST.allowed_domains == []
        assert render_readme_candidate.MANIFEST.execution_type == "deterministic_tool"

    def test_llm_mode_and_fixture_path_not_in_tool_schema(self):
        # These are real `execute()` parameters (deterministic test/wiring
        # callers only) but must never be offered to a planner.
        schema_props = render_readme_candidate.MANIFEST.to_tool_schema()["function"]["parameters"][
            "properties"
        ]
        assert "llm_mode" not in schema_props
        assert "fixture_response_path" not in schema_props


class TestVerifyReadmeCandidateCapability:
    """Wave 8b (`VER-001`): the independent verifier's own capability
    wrapper. `execute()`'s own delegation to `verification.checks::
    independently_verify_readme_candidate()` is confirmed here via
    monkeypatch -- the real re-derivation logic is proven end to end
    against a real work clone in `tests/unit/test_verification_checks.py`,
    not duplicated here."""

    def test_execute_delegates_to_independently_verify(self, monkeypatch):
        captured = {}

        def fake_verify(org_repo, final_text, status, needs_write):
            captured.update(
                org_repo=org_repo, final_text=final_text, status=status, needs_write=needs_write
            )
            return {"verdict": "accept", "reason": None, "checks": {}, "requirement_map": {}}

        monkeypatch.setattr(
            verify_readme_candidate, "independently_verify_readme_candidate", fake_verify
        )

        result = verify_readme_candidate.execute(
            "acme/widget",
            facts_hash="deadbeef",
            fresh_fingerprint="cafef00d",
            status="GENERATED",
            needs_write=True,
            final_text="# Widget\n",
        )

        assert result["verdict"] == "accept"
        assert captured == {
            "org_repo": "acme/widget",
            "final_text": "# Widget\n",
            "status": "GENERATED",
            "needs_write": True,
        }

    def test_manifest_is_scoped_to_independent_verification(self):
        assert verify_readme_candidate.MANIFEST.side_effect_class == "read_only_local"
        assert verify_readme_candidate.MANIFEST.allowed_domains == ["independent_verification"]
        assert verify_readme_candidate.MANIFEST.execution_type == "validator"

    def test_dispatch_denied_for_a_non_matching_caller_domain(self):
        from readme_agent.capabilities.dispatcher import dispatch_tool_call

        tool_call = {
            "function": {
                "name": "verify_readme_candidate",
                "arguments": (
                    '{"org_repo": "acme/widget", "facts_hash": "x", "fresh_fingerprint": "y", '
                    '"status": "GENERATED", "needs_write": true, "final_text": "# X\\n"}'
                ),
            }
        }
        result = dispatch_tool_call(
            tool_call, {"read_only_local"}, caller_domain="readme_presentation"
        )
        assert result.outcome == "rejected_domain_denied"


class _FakeBackendForFindings:
    def __init__(self, state: RunStateV1 | None):
        self._state = state

    def load(self, org_repo):
        return self._state


class TestStopCapability:
    """TC-17 (decision #46, `AGT-006`): a real, registered, schema-validated
    "stop" capability so a planner's stop intent is never confused with an
    unrecognized/hallucinated capability name in telemetry."""

    def test_manifest_is_unscoped_no_side_effect(self):
        assert stop.MANIFEST.allowed_domains == []
        assert stop.MANIFEST.side_effect_class == "read_only_local"
        assert stop.MANIFEST.capability_id == "stop"

    def test_all_tool_schemas_offers_it_unscoped(self):
        names = {s["function"]["name"] for s in registry.all_tool_schemas(caller_domain=None)}
        assert "stop" in names

    def test_execute_returns_stopped_with_reason(self):
        assert stop.execute(reason="nothing further to investigate") == {
            "stopped": True,
            "reason": "nothing further to investigate",
        }

    def test_execute_defaults_reason_to_empty_string(self):
        assert stop.execute() == {"stopped": True, "reason": ""}


class TestGetDomainFindings:
    """Wave 8.5 (`AGT-008`): on-demand, full-detail drill-down for one
    specialist domain's durably-recorded findings, complementing the
    bounded per-turn dossier summary every domain now gets."""

    def test_manifest_is_unscoped_and_read_only(self):
        assert get_domain_findings.MANIFEST.allowed_domains == []
        assert get_domain_findings.MANIFEST.side_effect_class == "read_only_network"
        assert get_domain_findings.MANIFEST.execution_type == "deterministic_tool"

    def test_all_tool_schemas_offers_it_unscoped(self):
        names = {s["function"]["name"] for s in registry.all_tool_schemas(caller_domain=None)}
        assert "get_domain_findings" in names

    def test_found_returns_full_details_for_the_recorded_domain(self):
        state = RunStateV1(
            org_repo="acme/widget",
            domain_states={
                "readme_reconciliation": DomainStateV1(
                    domain="readme_reconciliation",
                    accepted_status="CHANGED",
                    details={"license_claim": "MIT"},
                )
            },
        )
        result = get_domain_findings.execute(
            "acme/widget",
            "readme_reconciliation",
            state_backend=_FakeBackendForFindings(state),
        )
        assert result == {
            "found": True,
            "accepted_status": "CHANGED",
            "details": {"license_claim": "MIT"},
        }

    def test_not_found_when_domain_never_ran(self):
        state = RunStateV1(org_repo="acme/widget", domain_states={})
        result = get_domain_findings.execute(
            "acme/widget", "readme_reconciliation", state_backend=_FakeBackendForFindings(state)
        )
        assert result["found"] is False

    def test_not_found_when_no_backend_configured(self):
        result = get_domain_findings.execute("acme/widget", "readme_reconciliation")
        assert result["found"] is False

    def test_extra_kwargs_delivers_state_backend_via_dispatch(self):
        """AGT-008/Wave 8.5: the one deliberate exception to decision #26(b)'s
        "capabilities are stateless" rule -- wiring code (never the LLM)
        supplies `state_backend` via `dispatch_tool_call`'s `extra_kwargs`."""
        from readme_agent.capabilities.dispatcher import dispatch_tool_call

        state = RunStateV1(
            org_repo="acme/widget",
            domain_states={
                "readme_reconciliation": DomainStateV1(
                    domain="readme_reconciliation", accepted_status="NO_CHANGE", details={}
                )
            },
        )
        tool_call = {
            "function": {
                "name": "get_domain_findings",
                "arguments": '{"org_repo": "acme/widget", "domain": "readme_reconciliation"}',
            }
        }
        result = dispatch_tool_call(
            tool_call,
            {"read_only_network"},
            extra_kwargs={"state_backend": _FakeBackendForFindings(state)},
        )
        assert result.outcome == "executed"
        assert result.result == {"found": True, "accepted_status": "NO_CHANGE", "details": {}}

    def test_wiring_only_extra_kwarg_is_rejected_by_the_input_contract(self):
        """The LLM cannot inject a wiring-only argument into a capability call."""
        from readme_agent.capabilities.dispatcher import dispatch_tool_call

        tool_call = {
            "function": {
                "name": "get_domain_findings",
                "arguments": (
                    '{"org_repo": "acme/widget", "domain": "readme_reconciliation", '
                    '"state_backend": "hallucinated"}'
                ),
            }
        }
        result = dispatch_tool_call(
            tool_call,
            {"read_only_network"},
            extra_kwargs={"state_backend": _FakeBackendForFindings(None)},
        )
        assert result.outcome == "rejected_invalid_arguments"
        assert "state_backend" in result.error


class TestVerifyProseQuality:
    """Wave 8.6 (`VER-006` reversal): additive prose-quality check, domain-
    scoped identically to `verify_readme_candidate`."""

    def test_manifest_is_scoped_to_independent_verification(self):
        assert verify_prose_quality.MANIFEST.allowed_domains == ["independent_verification"]
        assert verify_prose_quality.MANIFEST.side_effect_class == "read_only_network"

    def test_execute_with_no_client_never_flags(self):
        result = verify_prose_quality.execute("acme/widget", "# Title\n\nNo owned span here.")
        assert result["flagged"] is False

    def test_execute_with_a_fixture_client_flags_and_corroborates(self):
        from readme_agent.llm.schema import LLMResponseMeta
        from readme_agent.llm.verifier_client import FixtureForcedToolClient, ForcedToolResult
        from readme_agent.readme.markers import render_span

        paragraph = "This is generic filler text about the product."
        final_text = "# Title\n\n" + render_span("resources", paragraph, "abc123")
        client = FixtureForcedToolClient(
            [
                ForcedToolResult(
                    arguments={
                        "flagged": True,
                        "quoted_span": "generic filler text",
                        "reason": "reads as generic",
                    },
                    meta=LLMResponseMeta(),
                )
            ]
        )
        result = verify_prose_quality.execute("acme/widget", final_text, client=client)
        assert result["flagged"] is True
        assert result["corroborated"] is True


class TestCompareAgainstPresentationStandard:
    """Wave 8.6: ongoing runtime comparison against docs/presentation-
    standard.md, replacing what was previously only one-time human research."""

    def test_manifest_is_scoped_to_presentation_benchmarking(self):
        assert compare_against_presentation_standard.MANIFEST.allowed_domains == [
            "presentation_benchmarking"
        ]

    def test_execute_with_candidate_text_and_fixture_client_returns_findings(self, monkeypatch):
        from readme_agent.llm.analysis_client import AnalysisResult, FixtureAnalysisClient
        from readme_agent.llm.schema import LLMResponseMeta
        from readme_agent.registry.models import ProductEntry

        fake_entry = ProductEntry(
            repo_name="widget",
            repo_url="https://github.com/acme/widget",
            clone_url="https://github.com/acme/widget.git",
            active=True,
            discovered_via="manual",
            mode="dry_run",
            ecosystem="java",
            family="widget",
            platform="java",
            policy_profile="test-profile",
        )
        monkeypatch.setattr(
            compare_against_presentation_standard, "require_listed", lambda org_repo: fake_entry
        )
        client = FixtureAnalysisClient(
            [
                AnalysisResult(
                    parsed={
                        "criteria_results": [
                            {"dimension": "Product clarity", "satisfied": True, "note": "ok"}
                        ],
                        "overall_summary": "Mostly compliant.",
                    },
                    meta=LLMResponseMeta(),
                )
            ]
        )

        result = compare_against_presentation_standard.execute(
            "acme/widget", "# Widget\n\nA widget library.\n", client=client
        )

        assert result["criteria_results"] == [
            {"dimension": "Product clarity", "satisfied": True, "note": "ok"}
        ]
        assert result["overall_summary"] == "Mostly compliant."


class TestCompareReferenceRepositories:
    """Wave 8.6: periodic (not per-run) capability -- re-fetches the
    reference repositories docs/presentation-standard.md's own research was
    based on."""

    def test_manifest_is_scoped_and_read_only(self):
        assert compare_reference_repositories.MANIFEST.allowed_domains == [
            "presentation_benchmarking"
        ]
        assert compare_reference_repositories.MANIFEST.side_effect_class == "read_only_network"

    def test_execute_hashes_each_reference_repos_readme(self, monkeypatch):
        monkeypatch.setattr(
            compare_reference_repositories,
            "get_file_content",
            lambda org_repo, path, token: f"content of {org_repo}".encode(),
        )

        result = compare_reference_repositories.execute()

        assert set(result["reference_readme_hashes"]) == set(
            compare_reference_repositories.REFERENCE_REPOSITORIES
        )
        assert all(not v.startswith("ERROR:") for v in result["reference_readme_hashes"].values())

    def test_a_single_unreachable_reference_does_not_hide_the_others(self, monkeypatch):
        def _flaky_get_file_content(org_repo, path, token):
            if org_repo == "n8n-io/n8n":
                raise RuntimeError("network unreachable")
            return b"content"

        monkeypatch.setattr(
            compare_reference_repositories, "get_file_content", _flaky_get_file_content
        )

        result = compare_reference_repositories.execute()

        assert result["reference_readme_hashes"]["n8n"].startswith("ERROR:")
        assert not result["reference_readme_hashes"]["pdfbox"].startswith("ERROR:")


class TestReviewVisualAssetAccuracy:
    """Wave 8.6 (item H): advisory-only vision-model accuracy review,
    reusing the existing VISUAL_PREPARATION domain."""

    def test_manifest_is_scoped_to_visual_preparation_and_advisory(self):
        assert review_visual_asset_accuracy.MANIFEST.allowed_domains == ["visual_preparation"]
        assert review_visual_asset_accuracy.MANIFEST.side_effect_class == "read_only_network"

    def test_execute_with_fixture_client_returns_structured_findings(self, monkeypatch):
        from readme_agent.llm.analysis_client import AnalysisResult, FixtureAnalysisClient
        from readme_agent.llm.schema import LLMResponseMeta
        from readme_agent.registry.models import ProductEntry

        fake_entry = ProductEntry(
            repo_name="widget",
            repo_url="https://github.com/acme/widget",
            clone_url="https://github.com/acme/widget.git",
            active=True,
            discovered_via="manual",
            mode="dry_run",
            ecosystem="java",
            family="widget",
            platform="java",
            policy_profile="test-profile",
        )
        monkeypatch.setattr(
            review_visual_asset_accuracy, "require_listed", lambda org_repo: fake_entry
        )
        monkeypatch.setattr(
            review_visual_asset_accuracy._visual_asset_ops,
            "find_existing_asset",
            lambda baseline_path: None,
        )
        monkeypatch.setattr(
            review_visual_asset_accuracy, "clone_baseline", lambda entry, path: None
        )
        client = FixtureAnalysisClient(
            [
                AnalysisResult(
                    parsed={
                        "depicts_unsupported_content": False,
                        "concerns": [],
                        "verdict": "accept",
                        "rationale": "Matches product facts.",
                    },
                    meta=LLMResponseMeta(),
                )
            ]
        )

        result = review_visual_asset_accuracy.execute("acme/widget", client=client)

        assert result["asset_source"] == "generated_candidate"
        assert result["depicts_unsupported_content"] is False
        assert result["verdict"] == "accept"


class TestGetTemplateCloneFindings:
    """Wave 8.6 (item I): reads the periodic embeddings batch job's output
    artifact for one org_repo -- evidence only, never a sole verdict."""

    def test_no_artifact_degrades_honestly(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            get_template_clone_findings, "_FINDINGS_PATH", tmp_path / "does-not-exist.json"
        )
        result = get_template_clone_findings.execute("acme/widget")
        assert result == {"found": False, "flagged": False, "flagged_against": []}

    def test_repo_never_embedded_returns_not_found(self, tmp_path, monkeypatch):
        artifact = tmp_path / "findings.json"
        artifact.write_text(
            json.dumps({"repos_embedded": ["other/repo"], "flagged_pairs": []}), encoding="utf-8"
        )
        monkeypatch.setattr(get_template_clone_findings, "_FINDINGS_PATH", artifact)

        result = get_template_clone_findings.execute("acme/widget")
        assert result["found"] is False

    def test_flagged_pair_reports_the_sibling_repo(self, tmp_path, monkeypatch):
        artifact = tmp_path / "findings.json"
        artifact.write_text(
            json.dumps(
                {
                    "repos_embedded": ["acme/widget", "acme/other"],
                    "flagged_pairs": [
                        {"repo_a": "acme/widget", "repo_b": "acme/other", "cosine_similarity": 0.9}
                    ],
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(get_template_clone_findings, "_FINDINGS_PATH", artifact)

        result = get_template_clone_findings.execute("acme/widget")
        assert result == {"found": True, "flagged": True, "flagged_against": ["acme/other"]}

    def test_embedded_but_not_flagged(self, tmp_path, monkeypatch):
        artifact = tmp_path / "findings.json"
        artifact.write_text(
            json.dumps({"repos_embedded": ["acme/widget"], "flagged_pairs": []}), encoding="utf-8"
        )
        monkeypatch.setattr(get_template_clone_findings, "_FINDINGS_PATH", artifact)

        result = get_template_clone_findings.execute("acme/widget")
        assert result == {"found": True, "flagged": False, "flagged_against": []}


class TestClassifyUpstreamChangeCapability:
    """Wave 6 (decision #39): the first capability scoped to a real domain
    (`readme_reconciliation`). Deliberately stateless -- the caller supplies
    the prior fingerprint, the capability never reads/writes durable state."""

    def test_execute_first_observation_when_no_prior_fingerprint(self, monkeypatch, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Widget\n\nSome content.\n", encoding="utf-8")
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="full")
        fake_inventory = SimpleNamespace(readme_path=readme)
        monkeypatch.setattr(classify_upstream_change, "require_listed", lambda org_repo: fake_entry)
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
        monkeypatch.setattr(classify_upstream_change, "require_listed", lambda org_repo: fake_entry)
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

    def test_execute_allows_disabled_repo(self, monkeypatch, tmp_path):
        """Decision #40: mode == "disabled" means push access is unverified,
        not "excluded from analysis" -- this read-only capability runs
        against every registered repo regardless of mode."""
        readme = tmp_path / "README.md"
        readme.write_text("# Widget\n\nSome content.\n", encoding="utf-8")
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="disabled")
        fake_inventory = SimpleNamespace(readme_path=readme)
        monkeypatch.setattr(classify_upstream_change, "require_listed", lambda org_repo: fake_entry)
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

    def test_execute_rejects_unknown_repo(self, monkeypatch):
        def _raise(org_repo):
            raise NotAllowlistedError(f"{org_repo} is not in data/products.json")

        monkeypatch.setattr(classify_upstream_change, "require_listed", _raise)

        with pytest.raises(NotAllowlistedError):
            classify_upstream_change.execute("acme/widget")

    def test_execute_extracts_license_claim_from_readme_text(self, monkeypatch, tmp_path):
        """Wave 7f: `license_claim` feeds `cross_surface_validation`'s
        comparison against `community_files_presentation`'s independently
        detected LICENSE file classification."""
        readme = tmp_path / "README.md"
        readme.write_text("# Widget\n\nLicensed under the MIT License.\n", encoding="utf-8")
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="full")
        fake_inventory = SimpleNamespace(readme_path=readme)
        monkeypatch.setattr(classify_upstream_change, "require_listed", lambda org_repo: fake_entry)
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

        assert result["license_claim"] == "MIT"


class TestAuditGithubGeneratedSurfacesCapability:
    """Wave 7b: the second domain-scoped capability, class E per
    docs/github-surface-control.md -- audit-only, forever, no renderer or
    write path exists or ever will."""

    def test_execute_wraps_the_github_api_client(self, monkeypatch):
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="dry_run")
        monkeypatch.setattr(
            audit_github_generated_surfaces, "require_listed", lambda org_repo: fake_entry
        )
        monkeypatch.setattr(audit_github_generated_surfaces.env, "gh_token", lambda: "fake-token")
        monkeypatch.setattr(
            audit_github_generated_surfaces,
            "repo_summary",
            lambda org_repo, token: {
                "language": "Java",
                "stargazers_count": 42,
                "forks_count": 7,
                "watchers_count": 42,
                "open_issues_count": 3,
            },
        )
        monkeypatch.setattr(
            audit_github_generated_surfaces,
            "list_contributors",
            lambda org_repo, token: [{"login": "alice"}, {"login": "bob"}],
        )
        monkeypatch.setattr(
            audit_github_generated_surfaces,
            "list_languages",
            lambda org_repo, token: {"Java": 12345},
        )

        result = audit_github_generated_surfaces.execute("acme/widget")

        assert result == {
            "contributors_count": 2,
            "primary_language": "Java",
            "languages": {"Java": 12345},
            "stargazers_count": 42,
            "forks_count": 7,
            "watchers_count": 42,
            "open_issues_count": 3,
        }

    def test_execute_rejects_unknown_repo(self, monkeypatch):
        def _raise(org_repo):
            raise NotAllowlistedError(f"{org_repo} is not in data/products.json")

        monkeypatch.setattr(audit_github_generated_surfaces, "require_listed", _raise)

        with pytest.raises(NotAllowlistedError):
            audit_github_generated_surfaces.execute("acme/widget")

    def test_manifest_is_scoped_read_only_network(self):
        assert audit_github_generated_surfaces.MANIFEST.side_effect_class == "read_only_network"
        assert audit_github_generated_surfaces.MANIFEST.allowed_domains == [
            "github_generated_surface_audit"
        ]
        assert audit_github_generated_surfaces.MANIFEST.execution_type == "read_only_audit"


class TestAuditPackageReleaseSurfacesCapability:
    """Wave 7c: the third domain-scoped capability, class D per
    docs/github-surface-control.md -- audit-only, forever; no write path for
    releases/packages, which stay product-agent owned (OWN-004/OWN-013)."""

    def test_execute_wraps_list_releases(self, monkeypatch):
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="dry_run")
        monkeypatch.setattr(
            audit_package_release_surfaces, "require_listed", lambda org_repo: fake_entry
        )
        monkeypatch.setattr(audit_package_release_surfaces.env, "gh_token", lambda: "fake-token")
        monkeypatch.setattr(
            audit_package_release_surfaces,
            "list_releases",
            lambda org_repo, token: [
                {"tag_name": "v2.0.0", "name": "Version 2.0.0"},
                {"tag_name": "v1.0.0", "name": "Version 1.0.0"},
            ],
        )

        result = audit_package_release_surfaces.execute("acme/widget")

        assert result == {
            "releases_count": 2,
            "latest_release_tag": "v2.0.0",
            "latest_release_name": "Version 2.0.0",
        }

    def test_execute_handles_no_releases(self, monkeypatch):
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="dry_run")
        monkeypatch.setattr(
            audit_package_release_surfaces, "require_listed", lambda org_repo: fake_entry
        )
        monkeypatch.setattr(audit_package_release_surfaces.env, "gh_token", lambda: None)
        monkeypatch.setattr(
            audit_package_release_surfaces, "list_releases", lambda org_repo, token: []
        )

        result = audit_package_release_surfaces.execute("acme/widget")

        assert result == {
            "releases_count": 0,
            "latest_release_tag": None,
            "latest_release_name": None,
        }

    def test_latest_release_is_chosen_by_published_at_not_api_return_order(self, monkeypatch):
        """TC-16 (Phase 13 finding): `list_releases()`'s pagination order is not
        guaranteed stable -- two content-identical calls that merely return the same
        releases in a different order must still agree on which one is "latest",
        or response-ordering noise alone can flip this domain's classification and
        falsely defeat the supervisor's convergence shortcut (SCL-006)."""
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="dry_run")
        monkeypatch.setattr(
            audit_package_release_surfaces, "require_listed", lambda org_repo: fake_entry
        )
        monkeypatch.setattr(audit_package_release_surfaces.env, "gh_token", lambda: "fake-token")
        content_identical_but_differently_ordered_calls = [
            [
                {
                    "tag_name": "v1.0.0",
                    "name": "Version 1.0.0",
                    "published_at": "2026-01-01T00:00:00Z",
                },
                {
                    "tag_name": "v2.0.0",
                    "name": "Version 2.0.0",
                    "published_at": "2026-06-01T00:00:00Z",
                },
            ],
            [
                {
                    "tag_name": "v2.0.0",
                    "name": "Version 2.0.0",
                    "published_at": "2026-06-01T00:00:00Z",
                },
                {
                    "tag_name": "v1.0.0",
                    "name": "Version 1.0.0",
                    "published_at": "2026-01-01T00:00:00Z",
                },
            ],
        ]
        results = []
        for releases in content_identical_but_differently_ordered_calls:
            monkeypatch.setattr(
                audit_package_release_surfaces,
                "list_releases",
                lambda org_repo, token, releases=releases: releases,
            )
            results.append(audit_package_release_surfaces.execute("acme/widget"))

        assert (
            results[0]
            == results[1]
            == {
                "releases_count": 2,
                "latest_release_tag": "v2.0.0",
                "latest_release_name": "Version 2.0.0",
            }
        )

    def test_draft_release_with_no_published_at_falls_back_to_created_at(self, monkeypatch):
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="dry_run")
        monkeypatch.setattr(
            audit_package_release_surfaces, "require_listed", lambda org_repo: fake_entry
        )
        monkeypatch.setattr(audit_package_release_surfaces.env, "gh_token", lambda: "fake-token")
        monkeypatch.setattr(
            audit_package_release_surfaces,
            "list_releases",
            lambda org_repo, token: [
                {
                    "tag_name": "v1.0.0",
                    "name": "Version 1.0.0",
                    "published_at": "2026-01-01T00:00:00Z",
                },
                {
                    "tag_name": "v2.0.0-draft",
                    "name": "Draft",
                    "published_at": None,
                    "created_at": "2026-06-01T00:00:00Z",
                },
            ],
        )

        result = audit_package_release_surfaces.execute("acme/widget")

        assert result["latest_release_tag"] == "v2.0.0-draft"

    def test_execute_rejects_unknown_repo(self, monkeypatch):
        def _raise(org_repo):
            raise NotAllowlistedError(f"{org_repo} is not in data/products.json")

        monkeypatch.setattr(audit_package_release_surfaces, "require_listed", _raise)

        with pytest.raises(NotAllowlistedError):
            audit_package_release_surfaces.execute("acme/widget")

    def test_manifest_is_scoped_read_only_network(self):
        assert audit_package_release_surfaces.MANIFEST.side_effect_class == "read_only_network"
        assert audit_package_release_surfaces.MANIFEST.allowed_domains == ["package_release_audit"]
        assert audit_package_release_surfaces.MANIFEST.execution_type == "read_only_audit"


class TestProposeMetadataChangesCapability:
    """Wave 7d: the fourth domain-scoped capability, class B per
    docs/github-surface-control.md -- dry-run proposal only; no PATCH is
    ever issued anywhere in this capability."""

    @staticmethod
    def _facts_result(*, all_metadata_facts: bool) -> dict:
        product_facts = migrate_product_facts_v1(
            ProductFactsV1(
                org_repo="acme/widget",
                family="widget",
                platform="java",
                ecosystem="java",
                products_org_link={"url": "https://products.example.org/widget/java/"},
            ),
            source_revision="abc123",
        )
        if all_metadata_facts:
            required_values = {
                "product.audience": ["Java developers"],
                "product.problems_solved": ["document processing"],
                "product.capabilities": ["read workbooks"],
                "product.formats": ["XLSX"],
            }
            facts = [
                (
                    fact.model_copy(
                        update={
                            "value": required_values[fact.field],
                            "verification_state": "policy_approved",
                            "confidence": 0.9,
                        }
                    )
                    if fact.field in required_values
                    else fact
                )
                for fact in product_facts.facts
            ]
            product_facts = ProductFactsV2(
                org_repo=product_facts.org_repo,
                facts=facts,
                selected_fact_ids=product_facts.selected_fact_ids,
            )
        return {
            "org_repo": "acme/widget",
            "family": "widget",
            "platform": "java",
            "ecosystem": "java",
            "products_org_link": {"url": "https://products.example.org/widget/java/"},
            "product_facts_v2": product_facts.model_dump(mode="json"),
        }

    def _mock(
        self,
        monkeypatch,
        *,
        description,
        homepage,
        topics,
        all_metadata_facts=True,
    ):
        monkeypatch.setattr(
            propose_metadata_changes,
            "collect_product_facts",
            lambda org_repo: self._facts_result(all_metadata_facts=all_metadata_facts),
        )
        monkeypatch.setattr(propose_metadata_changes.env, "gh_token", lambda: "fake-token")
        monkeypatch.setattr(
            propose_metadata_changes,
            "repo_summary",
            lambda org_repo, token: {
                "description": description,
                "homepage": homepage,
                "topics": topics,
            },
        )

    def test_proposes_description_and_homepage_when_both_missing(self, monkeypatch):
        self._mock(monkeypatch, description=None, homepage=None, topics=["java"])

        result = propose_metadata_changes.execute("acme/widget")

        assert result["proposed_description"] == "widget FOSS library for java"
        assert result["proposed_homepage"] == "https://products.example.org/widget/java/"
        assert result["proposed_topics"] is None  # "java" already present
        assert result["has_proposal"] is True
        assert result["blocked_findings"] == []
        assert result["fact_citations"]["metadata.homepage"] == ["documentation.links:primary"]

    def test_proposes_nothing_when_everything_already_present(self, monkeypatch):
        self._mock(
            monkeypatch,
            description="An existing description",
            homepage="https://example.org",
            topics=["java", "pdf"],
        )

        result = propose_metadata_changes.execute("acme/widget")

        assert result["proposed_description"] is None
        assert result["proposed_homepage"] is None
        assert result["proposed_topics"] is None
        assert result["has_proposal"] is False

    def test_never_second_guesses_an_existing_nonempty_value(self, monkeypatch):
        """OWN-006: an existing, non-empty description/homepage is never
        overwritten or judged -- only a missing field gets a proposal."""
        self._mock(monkeypatch, description="Already has one", homepage=None, topics=[])

        result = propose_metadata_changes.execute("acme/widget")

        assert result["proposed_description"] is None
        assert result["proposed_homepage"] == "https://products.example.org/widget/java/"

    def test_proposes_missing_topics_only(self, monkeypatch):
        self._mock(monkeypatch, description="x", homepage="https://x.org", topics=["unrelated"])

        result = propose_metadata_changes.execute("acme/widget")

        assert result["proposed_topics"] == ["java", "unrelated"]
        assert result["has_proposal"] is True

    def test_missing_fact_eligibility_blocks_generic_replacements(self, monkeypatch):
        self._mock(
            monkeypatch,
            description=None,
            homepage=None,
            topics=[],
            all_metadata_facts=False,
        )

        result = propose_metadata_changes.execute("acme/widget")

        assert result["has_proposal"] is True
        assert result["proposed_description"] is None
        assert result["proposed_homepage"] == "https://products.example.org/widget/java/"
        assert result["proposed_topics"] is None
        assert {finding["surface_id"] for finding in result["blocked_findings"]} == {
            "metadata.description",
            "metadata.topics",
        }

    def test_direct_dispatch_rejects_forged_eligibility_and_citations(self, monkeypatch):
        from readme_agent.capabilities.dispatcher import dispatch_tool_call

        self._mock(monkeypatch, description=None, homepage=None, topics=[])
        result = dispatch_tool_call(
            {
                "function": {
                    "name": "propose_metadata_changes",
                    "arguments": json.dumps(
                        {
                            "org_repo": "acme/widget",
                            "surface_eligibility": {"metadata.description": True},
                            "fact_citations": {"metadata.description": ["attacker:invented"]},
                        }
                    ),
                }
            },
            {"read_only_network"},
            caller_domain="metadata_presentation",
        )

        assert result.outcome == "rejected_invalid_arguments"

    def test_execute_rejects_unknown_repo(self, monkeypatch):
        def _raise(org_repo):
            raise NotAllowlistedError(f"{org_repo} is not in data/products.json")

        monkeypatch.setattr(propose_metadata_changes, "collect_product_facts", _raise)

        with pytest.raises(NotAllowlistedError):
            propose_metadata_changes.execute("acme/widget")

    def test_manifest_is_scoped_read_only_network(self):
        assert propose_metadata_changes.MANIFEST.side_effect_class == "read_only_network"
        assert propose_metadata_changes.MANIFEST.allowed_domains == ["metadata_presentation"]
        assert propose_metadata_changes.MANIFEST.execution_type == "read_only_audit"


class TestAuditCommunityFilesCapability:
    """Wave 7e: the fifth domain-scoped capability, class 1 per
    docs/github-surface-control.md -- a real eventual write path exists for
    this class, but this capability stops at audit + prepared candidate
    content; no write is ever attempted here."""

    def _mock(self, monkeypatch, *, inventory, profile_files, health_percentage=50):
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="dry_run")
        monkeypatch.setattr(audit_community_files, "require_listed", lambda org_repo: fake_entry)
        monkeypatch.setattr(
            audit_community_files,
            "paths",
            SimpleNamespace(baseline_dir=lambda org, repo: "fake-path"),
        )
        monkeypatch.setattr(audit_community_files, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(audit_community_files, "scan", lambda path: inventory)
        monkeypatch.setattr(audit_community_files.env, "gh_token", lambda: "fake-token")
        monkeypatch.setattr(
            audit_community_files,
            "get_community_profile",
            lambda org_repo, token: {
                "health_percentage": health_percentage,
                "files": profile_files,
            },
        )

    def test_execute_reports_presence_recognition_gap(self, monkeypatch, tmp_path):
        """The known, live-verified finding (docs/github-surface-control.md
        PF-3): real license content present locally that GitHub's Community
        Profile API does not recognize."""
        license_path = tmp_path / "LICENSE.txt"
        license_path.write_text("MIT License\n", encoding="utf-8")
        fake_inventory = SimpleNamespace(license_path=license_path, community_paths={})
        self._mock(
            monkeypatch,
            inventory=fake_inventory,
            profile_files={"license": None, "contributing": None, "code_of_conduct": None},
        )

        result = audit_community_files.execute("acme/widget")

        assert result["present_files"]["LICENSE"] is True
        assert result["recognized_files"]["LICENSE"] is False
        assert result["presence_recognition_gaps"] == ["LICENSE"]
        assert result["missing_files"] == ["CODE_OF_CONDUCT", "CONTRIBUTING", "SECURITY", "SUPPORT"]

    def test_execute_prepares_code_of_conduct_candidate_when_missing(self, monkeypatch):
        fake_inventory = SimpleNamespace(license_path=None, community_paths={})
        self._mock(
            monkeypatch,
            inventory=fake_inventory,
            profile_files={"license": None, "contributing": None, "code_of_conduct": None},
        )

        result = audit_community_files.execute("acme/widget")

        assert "CODE_OF_CONDUCT" in result["prepared_candidates"]
        candidate = result["prepared_candidates"]["CODE_OF_CONDUCT"]
        assert candidate["filename"] == "CODE_OF_CONDUCT.md"
        assert "Contributor Covenant" in candidate["content"]
        assert "CONTRIBUTING" not in result["prepared_candidates"]

    def test_execute_no_candidate_when_code_of_conduct_present(self, monkeypatch, tmp_path):
        license_path = tmp_path / "LICENSE"
        license_path.write_text("Apache License\nVersion 2.0\n", encoding="utf-8")
        fake_inventory = SimpleNamespace(
            license_path=license_path, community_paths={"CODE_OF_CONDUCT": "CODE_OF_CONDUCT.md"}
        )
        self._mock(
            monkeypatch,
            inventory=fake_inventory,
            profile_files={
                "license": {"spdx_id": "Apache-2.0"},
                "contributing": None,
                "code_of_conduct": {},
            },
        )

        result = audit_community_files.execute("acme/widget")

        assert result["present_files"]["CODE_OF_CONDUCT"] is True
        assert result["prepared_candidates"] == {}

    def test_execute_detects_license_from_github_spdx_id_first(self, monkeypatch, tmp_path):
        """Wave 7f: `detected_license` reuses `license.auditor.detect_license()`
        -- GitHub's own SPDX classification wins over file-content
        classification when both are available."""
        license_path = tmp_path / "LICENSE"
        license_path.write_text("MIT License\n", encoding="utf-8")
        fake_inventory = SimpleNamespace(license_path=license_path, community_paths={})
        self._mock(
            monkeypatch,
            inventory=fake_inventory,
            profile_files={
                "license": {"spdx_id": "Apache-2.0"},
                "contributing": None,
                "code_of_conduct": None,
            },
        )

        result = audit_community_files.execute("acme/widget")

        assert result["detected_license"] == "Apache-2.0"

    def test_execute_falls_back_to_file_content_when_github_spdx_is_null(
        self, monkeypatch, tmp_path
    ):
        """The real, documented `cells-java` case: GitHub reports no SPDX
        classification, but the LICENSE file's own content is real MIT text."""
        license_path = tmp_path / "LICENSE.txt"
        license_path.write_text("MIT License\n", encoding="utf-8")
        fake_inventory = SimpleNamespace(license_path=license_path, community_paths={})
        self._mock(
            monkeypatch,
            inventory=fake_inventory,
            profile_files={"license": None, "contributing": None, "code_of_conduct": None},
        )

        result = audit_community_files.execute("acme/widget")

        assert result["detected_license"] == "MIT"

    def test_execute_rejects_unknown_repo(self, monkeypatch):
        def _raise(org_repo):
            raise NotAllowlistedError(f"{org_repo} is not in data/products.json")

        monkeypatch.setattr(audit_community_files, "require_listed", _raise)

        with pytest.raises(NotAllowlistedError):
            audit_community_files.execute("acme/widget")

    def test_manifest_is_scoped_read_only_network(self):
        assert audit_community_files.MANIFEST.side_effect_class == "read_only_network"
        assert audit_community_files.MANIFEST.allowed_domains == ["community_files_presentation"]
        assert audit_community_files.MANIFEST.execution_type == "read_only_audit"


def _init_work_repo(tmp_path, readme_text="# Widget\n"):
    from readme_agent.gitsafety._git import run_git

    work_path = tmp_path / "work"
    work_path.mkdir()
    run_git(["init", "-b", "main"], cwd=work_path)
    run_git(["config", "user.email", "test@example.com"], cwd=work_path)
    run_git(["config", "user.name", "Test"], cwd=work_path)
    (work_path / "README.md").write_text(readme_text, encoding="utf-8")
    run_git(["add", "."], cwd=work_path)
    run_git(["commit", "-m", "initial"], cwd=work_path)
    return work_path


class TestCommitReadmeWriteCapability:
    """Wave 7g: the one real mutating capability this project registers.
    Real local git repos throughout (no git mocking) -- exercises the actual
    write + git-commit path, matching this project's own convention of
    proving anything touching gitsafety against real git plumbing."""

    def _mock(self, monkeypatch, work_path, *, mode):
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode=mode)
        monkeypatch.setattr(commit_readme_write, "require_permitted", lambda org_repo: fake_entry)
        monkeypatch.setattr(
            commit_readme_write, "paths", SimpleNamespace(work_dir=lambda org, repo: work_path)
        )

    def test_execute_writes_and_commits_when_mode_full_and_generated(self, monkeypatch, tmp_path):
        work_path = _init_work_repo(tmp_path)
        self._mock(monkeypatch, work_path, mode="full")

        result = commit_readme_write.execute(
            "acme/widget",
            facts_hash="deadbeef1234",
            fresh_fingerprint="cafef00d",
            status="GENERATED",
            needs_write=True,
            final_text="# Widget\n\nUpdated content.\n",
            verification_verdict="accept",
        )

        assert result == {"written": True, "committed": True}
        assert (work_path / "README.md").read_text(
            encoding="utf-8"
        ) == "# Widget\n\nUpdated content.\n"

    def test_execute_writes_but_does_not_commit_when_mode_dry_run(self, monkeypatch, tmp_path):
        """The safety-critical gate: mode != 'full' still writes the file
        (a specialist may legitimately render+persist locally for a
        dry-run pilot) but never makes a real git commit."""
        work_path = _init_work_repo(tmp_path)
        self._mock(monkeypatch, work_path, mode="dry_run")

        result = commit_readme_write.execute(
            "acme/widget",
            facts_hash="deadbeef1234",
            fresh_fingerprint="cafef00d",
            status="GENERATED",
            needs_write=True,
            final_text="# Widget\n\nUpdated content.\n",
            verification_verdict="accept",
        )

        assert result == {"written": True, "committed": False}

    def test_execute_does_not_write_when_needs_write_is_false(self, monkeypatch, tmp_path):
        work_path = _init_work_repo(tmp_path)
        original = (work_path / "README.md").read_text(encoding="utf-8")
        self._mock(monkeypatch, work_path, mode="full")

        result = commit_readme_write.execute(
            "acme/widget",
            facts_hash="deadbeef1234",
            fresh_fingerprint="cafef00d",
            status="COMPLIANT_NO_CHANGE",
            needs_write=False,
            final_text=original,
            verification_verdict="accept",
        )

        assert result == {"written": False, "committed": False}
        assert (work_path / "README.md").read_text(encoding="utf-8") == original

    def test_execute_rejects_unknown_repo(self, monkeypatch):
        def _raise(org_repo):
            raise NotAllowlistedError(f"{org_repo} is not in data/products.json")

        monkeypatch.setattr(commit_readme_write, "require_permitted", _raise)

        with pytest.raises(NotAllowlistedError):
            commit_readme_write.execute(
                "acme/widget",
                facts_hash="x",
                fresh_fingerprint="y",
                status="GENERATED",
                needs_write=True,
                final_text="# X\n",
                verification_verdict="accept",
            )

    def test_manifest_is_scoped_local_write_with_idempotency_declared(self):
        assert commit_readme_write.MANIFEST.side_effect_class == "local_write"
        assert commit_readme_write.MANIFEST.allowed_domains == ["readme_presentation"]
        assert commit_readme_write.MANIFEST.idempotency_inputs == [
            "org_repo",
            "facts_hash",
            "fresh_fingerprint",
            "final_text",
        ]
        assert commit_readme_write.MANIFEST.retry_policy == "idempotent_only"

    def test_precheck_accepts_the_real_verification_token(self):
        """TC-15 (decision #46, F3): precheck() now requires the exact
        re-derivable token compute_verification_token() produces for these
        arguments -- not a plain literal string."""
        from readme_agent.verification.checks import compute_verification_token

        arguments = {
            "org_repo": "acme/widget",
            "facts_hash": "deadbeef1234",
            "fresh_fingerprint": "cafef00d",
            "verification_nonce": "run-nonce-abc",
        }
        token = compute_verification_token(
            arguments["org_repo"],
            arguments["facts_hash"],
            arguments["fresh_fingerprint"],
            arguments["verification_nonce"],
        )
        assert commit_readme_write.precheck({**arguments, "verification_verdict": token}) is None

    def test_precheck_rejects_a_token_computed_with_a_different_nonce(self):
        """TC-28 (decision #46's own deferred scope from TC-15): a token that
        is real and correctly derived for THIS call's org_repo/facts_hash/
        fresh_fingerprint, but minted with a DIFFERENT nonce (i.e. replayed
        from a different run), must not be accepted -- proving the nonce
        actually closes the cross-run replay gap TC-15 left open, not just
        that it's threaded through somewhere."""
        from readme_agent.verification.checks import compute_verification_token

        replayed_token = compute_verification_token(
            "acme/widget", "deadbeef1234", "cafef00d", "a-previous-runs-nonce"
        )
        reason = commit_readme_write.precheck(
            {
                "org_repo": "acme/widget",
                "facts_hash": "deadbeef1234",
                "fresh_fingerprint": "cafef00d",
                "verification_verdict": replayed_token,
                "verification_nonce": "this-runs-nonce",
            }
        )
        assert reason is not None
        assert "does not match" in reason

    def test_precheck_rejects_a_hardcoded_accept_literal(self):
        """The exact regression F3 found: a caller (or a future wiring bug
        that skips _verify_node) that just types the literal "accept"
        string must no longer pass -- proving this is a real structural
        check, not the plain string comparison it used to be."""
        reason = commit_readme_write.precheck(
            {
                "org_repo": "acme/widget",
                "facts_hash": "deadbeef1234",
                "fresh_fingerprint": "cafef00d",
                "verification_verdict": "accept",
            }
        )
        assert reason is not None
        assert "does not match" in reason

    def test_precheck_rejects_a_token_computed_for_different_content(self):
        """A token that's real (correctly derived by compute_verification_
        token) but for DIFFERENT facts_hash/fresh_fingerprint than this call
        declares must not be accepted -- the token is bound to the exact
        candidate it was issued for, not just "any real-looking token"."""
        from readme_agent.verification.checks import compute_verification_token

        stale_token = compute_verification_token(
            "acme/widget", "old-hash", "old-fingerprint", "some-nonce"
        )
        reason = commit_readme_write.precheck(
            {
                "org_repo": "acme/widget",
                "facts_hash": "deadbeef1234",
                "fresh_fingerprint": "cafef00d",
                "verification_verdict": stale_token,
            }
        )
        assert reason is not None

    def test_precheck_rejects_a_missing_verdict(self):
        reason = commit_readme_write.precheck({})
        assert reason is not None


class TestCommitReadmeWriteReconciliationCheck:
    """`EFF-001`'s remaining gap, closed for real: re-reads the work clone's
    own README content to answer "did this effect already land" without
    trusting the ledger's own possibly-stale pending record."""

    def _init_work_repo_with_span(self, tmp_path, facts_hash):
        from readme_agent.gitsafety._git import run_git
        from readme_agent.readme.markers import upsert_span

        work_path = tmp_path / "work"
        work_path.mkdir()
        run_git(["init", "-b", "main"], cwd=work_path)
        run_git(["config", "user.email", "test@example.com"], cwd=work_path)
        run_git(["config", "user.name", "Test"], cwd=work_path)
        text = upsert_span("# Widget\n", "resources", "https://example.org\n", facts_hash)
        (work_path / "README.md").write_text(text, encoding="utf-8")
        run_git(["add", "."], cwd=work_path)
        run_git(
            ["commit", "-m", f"readme-agent: close promotional gaps ({facts_hash[:12]})"],
            cwd=work_path,
        )
        return work_path

    def _mock(self, monkeypatch, work_path):
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="full")
        monkeypatch.setattr(commit_readme_write, "find_entry", lambda org_repo: fake_entry)
        monkeypatch.setattr(
            commit_readme_write, "paths", SimpleNamespace(work_dir=lambda org, repo: work_path)
        )

    def test_returns_match_when_embedded_facts_hash_agrees(self, monkeypatch, tmp_path):
        facts_hash = "abc123def456"
        work_path = self._init_work_repo_with_span(tmp_path, facts_hash)
        self._mock(monkeypatch, work_path)

        result = commit_readme_write.reconciliation_check(
            {"org_repo": "acme/widget", "facts_hash": facts_hash}
        )

        assert result == {"written": True, "committed": True}

    def test_returns_none_when_facts_hash_disagrees(self, monkeypatch, tmp_path):
        work_path = self._init_work_repo_with_span(tmp_path, "abc123def456")
        self._mock(monkeypatch, work_path)

        result = commit_readme_write.reconciliation_check(
            {"org_repo": "acme/widget", "facts_hash": "some-other-hash"}
        )

        assert result is None

    def test_returns_none_when_no_work_clone_exists(self, monkeypatch, tmp_path):
        fake_entry = SimpleNamespace(org="acme", repo_name="widget", mode="full")
        monkeypatch.setattr(commit_readme_write, "find_entry", lambda org_repo: fake_entry)
        monkeypatch.setattr(
            commit_readme_write,
            "paths",
            SimpleNamespace(work_dir=lambda org, repo: tmp_path / "nonexistent"),
        )

        result = commit_readme_write.reconciliation_check(
            {"org_repo": "acme/widget", "facts_hash": "abc123"}
        )

        assert result is None

    def test_returns_none_when_org_repo_unknown(self, monkeypatch):
        monkeypatch.setattr(commit_readme_write, "find_entry", lambda org_repo: None)

        result = commit_readme_write.reconciliation_check(
            {"org_repo": "acme/widget", "facts_hash": "abc123"}
        )

        assert result is None


class TestPrepareVisualAssetCapability:
    """Wave 7h: the eighth domain-scoped capability, and the first to use
    `execution_type="manual_delivery_preparation"`. Prepare-only -- never
    writes or embeds anything into the repository or README.md."""

    def _mock(self, monkeypatch, baseline_path):
        fake_entry = SimpleNamespace(
            org="acme", repo_name="widget", family="widget", platform="java", mode="dry_run"
        )
        monkeypatch.setattr(prepare_visual_asset, "require_listed", lambda org_repo: fake_entry)
        monkeypatch.setattr(prepare_visual_asset, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(
            prepare_visual_asset,
            "paths",
            SimpleNamespace(baseline_dir=lambda org, repo: baseline_path),
        )

    def test_prepares_a_candidate_banner_when_no_asset_exists(self, monkeypatch, tmp_path):
        self._mock(monkeypatch, tmp_path)

        result = prepare_visual_asset.execute("acme/widget")

        assert result["existing_asset_found"] is False
        assert result["existing_asset_path"] is None
        assert result["format"] == "PNG"
        assert result["size_within_reasonable_bounds"] is True
        assert result["concerns"] == []
        assert result["prepared_candidate"]["filename"] == "banner.png"
        assert "no external or copied content" in result["license_status"]

    def test_validates_an_existing_asset_when_one_is_found(self, monkeypatch, tmp_path):
        from PIL import Image

        (tmp_path / "docs").mkdir()
        Image.new("RGB", (400, 100), color="blue").save(tmp_path / "docs" / "logo.png")
        self._mock(monkeypatch, tmp_path)

        result = prepare_visual_asset.execute("acme/widget")

        assert result["existing_asset_found"] is True
        assert result["existing_asset_path"] == str(Path("docs") / "logo.png")
        assert result["width"] == 400
        assert result["height"] == 100
        assert result["prepared_candidate"] is None
        assert "human review required" in result["license_status"]

    def test_flags_an_oversized_existing_asset(self, monkeypatch, tmp_path):
        from PIL import Image

        Image.new("RGB", (5000, 5000), color="red").save(tmp_path / "huge.png")
        self._mock(monkeypatch, tmp_path)

        result = prepare_visual_asset.execute("acme/widget")

        assert result["size_within_reasonable_bounds"] is False
        assert result["concerns"] != []

    def test_svg_asset_skips_dimension_checks(self, monkeypatch, tmp_path):
        (tmp_path / "logo.svg").write_text("<svg></svg>", encoding="utf-8")
        self._mock(monkeypatch, tmp_path)

        result = prepare_visual_asset.execute("acme/widget")

        assert result["existing_asset_found"] is True
        assert result["format"] == "SVG"
        assert result["width"] is None

    def test_execute_rejects_unknown_repo(self, monkeypatch):
        def _raise(org_repo):
            raise NotAllowlistedError(f"{org_repo} is not in data/products.json")

        monkeypatch.setattr(prepare_visual_asset, "require_listed", _raise)

        with pytest.raises(NotAllowlistedError):
            prepare_visual_asset.execute("acme/widget")

    def test_manifest_is_scoped_read_only_local(self):
        assert prepare_visual_asset.MANIFEST.side_effect_class == "read_only_local"
        assert prepare_visual_asset.MANIFEST.allowed_domains == ["visual_preparation"]
        assert prepare_visual_asset.MANIFEST.execution_type == "manual_delivery_preparation"


class TestRequirementIdsDrift:
    """Wave 8c (requirement mapping): `CapabilityManifest.requirement_ids`
    couples code to `plans/requirements.md`, a document planning sessions
    actively renumber/edit -- with zero enforced consistency check otherwise.
    Reuses `plans/investigations/tools/extract_requirements.py`'s own proven
    row-matching regex (`GOV-015`: reuse, don't reimplement a second parser)
    by loading it as a module (never executing its `main()`, which would
    write `plans/investigations/control/normalized-requirements-inventory.
    yaml` as an unwanted side effect of running the test suite) -- fresh
    against the current `plans/requirements.md`, not a possibly-stale
    pre-generated snapshot."""

    def _known_requirement_ids(self) -> set[str]:
        import importlib.util

        repo_root = Path(__file__).resolve().parents[2]
        module_path = repo_root / "plans" / "investigations" / "tools" / "extract_requirements.py"
        spec = importlib.util.spec_from_file_location("extract_requirements", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # module-level code only -- `main()` is never called

        text = (repo_root / "plans" / "requirements.md").read_text(encoding="utf-8")
        return {m.group("id") for line in text.splitlines() if (m := module.ROW_RE.match(line))}

    def test_every_declared_requirement_id_exists_in_requirements_md(self):
        known_ids = self._known_requirement_ids()
        assert len(known_ids) > 0  # sanity: the parser actually matched real rows

        for manifest in registry.list_all():
            unknown = set(manifest.requirement_ids) - known_ids
            assert not unknown, (
                f"{manifest.capability_id!r} declares requirement_ids {sorted(unknown)} "
                "that do not exist in plans/requirements.md"
            )
