"""Tests for the readme_reconciliation specialist (Wave 6, decision #39) and
the specialist registry -- real local git repos, real capability dispatch
through classify_upstream_change (proving decision #34's domain enforcement
end to end, not mocked), a fake in-memory StateBackend. No network."""

import json
from pathlib import Path

import pytest

from readme_agent.capabilities import review_visual_asset_accuracy, verify_prose_quality
from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import reset_clone_memo
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.client import GeneratedResult
from readme_agent.llm.schema import LLMBlockResponse, LLMResponseMeta
from readme_agent.llm.verifier_client import ForcedToolResult
from readme_agent.profile import cached
from readme_agent.readme import candidate_pipeline
from readme_agent.specialists import readme_reconciliation, registry
from readme_agent.state.backend import SaveResult
from readme_agent.state.schema import DomainStateV1, RunStateV1

ORG_REPO = "example-foss/Example-Widget"
REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _clean_clone_memo():
    """Found live, 2026-07-22: `gitsafety.clone._baseline_clone_memo` (the
    SCL-004-extension memoization added the same day) is only invalidated by
    `supervisor/loop.py::supervise_repo()`'s own explicit call -- a "process is
    one supervise/CLI run" assumption that holds for real production
    invocations (each a fresh process) but not for this file's own tests,
    several of which call a specialist's `run()` (or, transitively,
    `orchestrator.prepare_readme_candidate()`) more than once in the SAME test
    process for the SAME org_repo, each time expecting genuinely current
    upstream state. Without this reset, the second call silently reused the
    first call's now-stale baseline clone -- confirmed via a real, reproduced
    regression (`test_upstream_edit_between_runs_is_upstream_changed`,
    `test_a_success_after_failures_resets_the_counter`, both passed clean
    against the last real commit, both failed 100%-reproducibly once this
    memoization landed uncommitted). Mirrors `test_gitsafety.py`'s own
    identical fixture, added for the identical reason when the memo was
    introduced -- this file just didn't get the matching update."""
    reset_clone_memo()
    yield
    reset_clone_memo()


# Proven-valid against the real word-count/prohibited-terms/talking-points
# rules (test_orchestrator.py's own FIXTURE_RESPONSE, against an identical
# policy) -- reused verbatim rather than hand-rolling a second sentence.
_FIXTURE_RELATIONSHIP_PARAGRAPH = (
    "This repository is the free, open-source FOSS edition of the "
    "corresponding commercial Example product. Upgrade to the commercial "
    "edition when you need a broader feature set or dedicated support."
)


class _FakeLiveLLMClient:
    """Wave 7g: readme_presentation's render step can reach the one real
    LLM call -- faked so this file's real-local-git-repo tests stay
    network-free, matching this project's own `@pytest.mark.live` convention."""

    def __init__(self, *args, **kwargs):
        pass

    def generate(self, messages: list[dict[str, str]]) -> GeneratedResult:
        return GeneratedResult(
            response=LLMBlockResponse(
                relationship_paragraph=_FIXTURE_RELATIONSHIP_PARAGRAPH,
                talking_points_covered=["open_source_scope", "commercial_upgrade_path"],
            ),
            meta=LLMResponseMeta(),
            mode="fixture",
        )


class _FakeNonFlaggingForcedToolClient:
    """Wave 8.6 (`VER-006` reversal): `readme_presentation`'s `_verify_node`
    now additionally dispatches `verify_prose_quality` after a deterministic
    accept -- faked here (never flagged) so this file's real-local-git-repo
    tests stay network-free and their existing accept/commit assertions are
    unaffected, matching `_FakeLiveLLMClient`'s own established convention
    one class up."""

    def __init__(self, *args, **kwargs):
        pass

    def call(self, messages, tool_schema):
        return ForcedToolResult(
            arguments={"flagged": False, "reason": "fixture: never flagged"}, meta=LLMResponseMeta()
        )


class _FakeNonFlaggingAnalysisClient:
    """Wave 8.6 (item H): `visual_preparation`'s classify step is followed
    by an additive, advisory-only vision-accuracy review -- faked here
    (never flags) so this file's real-local-git-repo tests stay network-free."""

    def __init__(self, *args, **kwargs):
        pass

    def analyze(self, messages):
        return AnalysisResult(
            parsed={
                "depicts_unsupported_content": False,
                "concerns": [],
                "verdict": "accept",
                "rationale": "fixture: not reviewed",
            },
            meta=LLMResponseMeta(),
        )


def _init_source_repo(path, readme_text: str):
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-b", "main"], cwd=path)
    run_git(["config", "user.email", "test@example.com"], cwd=path)
    run_git(["config", "user.name", "Test"], cwd=path)
    (path / "README.md").write_text(readme_text, encoding="utf-8")
    run_git(["add", "."], cwd=path)
    run_git(["commit", "-m", "initial"], cwd=path)
    return path


_POLICY_YAML = """schema_version: 2
policy_profile: test-profile
required_elements:
  license_mentioned:
    detected_license: MIT
  products_org_link:
    url: "https://products.example.org/widget/java/"
    family_url: "https://products.example.org/widget/"
    label: "Example Widget"
  products_com_link:
    url: "https://products.example.com/widget/java/"
    family_url: "https://products.example.com/widget"
    label: "Example Widget"
  relationship_explained:
    min_sentences: 2
    talking_points: [open_source_scope, commercial_upgrade_path]
secondary_links: []
block:
  word_limit: { min: 10, max: 200 }
  prohibited_terms: ["guarantee"]
  link_whitelist_domains: [products.example.com, products.example.org]
"""


def _setup_project_root(tmp_path, source_clone_url: str):
    (tmp_path / "data").mkdir()
    # metadata_presentation's specialist dispatches get_product_facts, which
    # needs a real config/policies/*.yml -- present unconditionally so every
    # test class in this file can exercise any specialist.
    (tmp_path / "config" / "policies").mkdir(parents=True)
    (tmp_path / "config" / "policies" / "test-profile.yml").write_text(
        _POLICY_YAML, encoding="utf-8"
    )
    # Wave 8.5: llm.prompts.prompt_content_hash() reads
    # prompts/generation/relationship_explained.yaml fresh, cwd-relative, on
    # every call (readme_presentation's render step calls build_prompt()
    # whenever relationship_explained is a real gap, regardless of llm_mode)
    # -- staged unconditionally, same as test_orchestrator.py's own
    # _setup_project_root(), so every test class in this file can exercise
    # readme_presentation too. build_prompt() itself reads from the eagerly
    # import-time-cached prompt_registry instead, unaffected by cwd.
    prompt_dir = tmp_path / "prompts" / "generation"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "relationship_explained.yaml").write_text(
        (REPO_ROOT / "prompts" / "generation" / "relationship_explained.yaml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    products = [
        {
            "family": "widget",
            "platform": "java",
            "repo_name": "Example-Widget",
            "repo_url": "https://github.com/example-foss/Example-Widget",
            "clone_url": source_clone_url,
            "active": True,
            "discovered_via": "manual",
            "mode": "full",
            "ecosystem": "java",
            "policy_profile": "test-profile",
        }
    ]
    (tmp_path / "data" / "products.json").write_text(json.dumps(products), encoding="utf-8")


class _FakeStateBackend:
    """Mirrors test_orchestrator.py's own fake backend -- lock is a no-op
    (always granted), full CAS/lock contract is proven elsewhere
    (test_state_backend.py)."""

    def __init__(self):
        self._states: dict[str, RunStateV1] = {}

    def load(self, org_repo):
        return self._states.get(org_repo)

    def save(self, org_repo, state, expected_version):
        current = self._states.get(org_repo)
        current_version = current.state_version if current else None
        if expected_version != current_version:
            return SaveResult(outcome="stale", new_version=current_version)
        new_version = (current_version or 0) + 1
        self._states[org_repo] = state.model_copy(update={"state_version": new_version})
        return SaveResult(outcome="saved", new_version=new_version)

    def acquire_lock(self, org_repo):
        return object()

    def release_lock(self, lock):
        pass

    def lock_still_held(self, lock):
        # Lock is a no-op (always granted, never reclaimed) in this fake --
        # see the class docstring.
        return True

    def load_model_route_status(self, job):
        # Wave 13.4 (`LLM-020`): `None` means "enabled" (the permissive
        # default) -- no test in this file exercises a disabled route via
        # this fake; that's proven directly in test_capability_dispatcher.py.
        return None


class TestSpecialistsRegistry:
    def test_all_domains_includes_all_ten_registered_specialists(self):
        assert registry.all_domains() == [
            "readme_reconciliation",
            "github_generated_surface_audit",
            "package_release_audit",
            "metadata_presentation",
            "community_files_presentation",
            "cross_surface_validation",
            "readme_presentation",
            "visual_preparation",
            "presentation_benchmarking",
            "independent_verification",
        ]

    def test_run_domain_unknown_domain_returns_none(self):
        assert registry.run_domain("nonexistent_domain", "acme/widget", None) is None

    def test_run_domain_dispatches_to_the_real_specialist(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)

        result = registry.run_domain("readme_reconciliation", ORG_REPO, None)

        assert result is not None
        assert result.accepted_status == "FIRST_OBSERVATION"


class TestSpecialistsRegistryCompletenessGate:
    """Wave 7: the reverse direction of the existing domain-membership check
    -- a domain registered in capabilities/domains.py::KNOWN_DOMAINS with no
    matching specialist must fail loudly at build time, not silently produce
    a domain that never reports anything."""

    def test_orphaned_domain_with_no_specialist_raises(self, monkeypatch):
        from readme_agent.capabilities import domains
        from readme_agent.errors import ConfigError

        monkeypatch.setattr(
            domains,
            "KNOWN_DOMAINS",
            frozenset(
                {
                    "readme_reconciliation",
                    "github_generated_surface_audit",
                    "package_release_audit",
                    "metadata_presentation",
                    "community_files_presentation",
                    "cross_surface_validation",
                    "readme_presentation",
                    "visual_preparation",
                    "presentation_benchmarking",
                    "independent_verification",
                    "orphaned_domain",
                }
            ),
        )
        with pytest.raises(ConfigError, match="orphaned_domain"):
            registry._build(registry._SPECIALISTS)

    def test_real_registry_has_no_orphaned_domains(self):
        registry._build(registry._SPECIALISTS)  # must not raise


class TestSpecialistsRegistryDependsOnOrdering:
    """Wave 7f: `SpecialistManifest.depends_on` -- "registered last sees
    siblings' this-run state" was mechanically true from dict insertion
    order alone, but structurally unenforced. This build-time gate makes it
    a checked invariant instead."""

    def test_dependency_registered_earlier_does_not_raise(self, monkeypatch):
        from readme_agent.capabilities import domains

        monkeypatch.setattr(domains, "KNOWN_DOMAINS", frozenset({"a", "b"}))
        specialists = (
            registry.SpecialistManifest(
                domain="a", name="A", purpose="p", run=lambda org_repo, backend: None
            ),
            registry.SpecialistManifest(
                domain="b",
                name="B",
                purpose="p",
                run=lambda org_repo, backend: None,
                depends_on=("a",),
            ),
        )
        registry._build(specialists)  # must not raise

    def test_dependency_not_yet_registered_raises(self, monkeypatch):
        from readme_agent.capabilities import domains
        from readme_agent.errors import ConfigError

        monkeypatch.setattr(domains, "KNOWN_DOMAINS", frozenset({"a", "b"}))
        specialists = (
            registry.SpecialistManifest(
                domain="b",
                name="B",
                purpose="p",
                run=lambda org_repo, backend: None,
                depends_on=("a",),
            ),
            registry.SpecialistManifest(
                domain="a", name="A", purpose="p", run=lambda org_repo, backend: None
            ),
        )
        with pytest.raises(ConfigError, match="depends_on"):
            registry._build(specialists)

    def test_real_registry_satisfies_its_own_declared_dependencies(self):
        """cross_surface_validation's real depends_on against the real,
        ordered _SPECIALISTS tuple -- not a synthetic fixture."""
        registry._build(registry._SPECIALISTS)  # must not raise


class TestReadmeReconciliationSpecialist:
    def test_first_run_is_first_observation_and_records_state(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()

        result = readme_reconciliation.run(ORG_REPO, backend)

        assert result.accepted_status == "FIRST_OBSERVATION"
        assert result.domain == "readme_reconciliation"
        stored = backend.load(ORG_REPO)
        assert stored is not None
        assert stored.domain_states["readme_reconciliation"].accepted_status == "FIRST_OBSERVATION"

    def test_second_run_with_unchanged_content_is_no_change(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()

        first = readme_reconciliation.run(ORG_REPO, backend)
        assert first.accepted_status == "FIRST_OBSERVATION"

        second = readme_reconciliation.run(ORG_REPO, backend)
        assert second.accepted_status == "NO_CHANGE"

    def test_upstream_edit_between_runs_is_upstream_changed(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()

        first = readme_reconciliation.run(ORG_REPO, backend)
        assert first.accepted_status == "FIRST_OBSERVATION"

        (source / "README.md").write_text(
            "# Widget\n\nA widget library.\n\nNew section a maintainer added.\n", encoding="utf-8"
        )
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "docs: update"], cwd=source)
        # Simulates the process boundary supervise_repo() gets for free via its
        # own invalidate_baseline_clone() call -- this test calls the
        # specialist directly, so it must reset the memo itself, the same way
        # test_gitsafety.py's own tests do for the identical reason.
        reset_clone_memo()

        second = readme_reconciliation.run(ORG_REPO, backend)
        assert second.accepted_status == "UPSTREAM_CHANGED"

    def test_run_without_a_backend_still_works(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)

        result = readme_reconciliation.run(ORG_REPO, None)

        assert result.accepted_status == "FIRST_OBSERVATION"


class TestPackageReleaseAuditSpecialist:
    """Wave 7c: dispatches two capabilities (the new, domain-scoped
    audit_package_release_surfaces, and the existing, unscoped
    check_install_path) rather than reimplementing package resolution."""

    def _mock_network(self, monkeypatch, *, releases, install_path_resolved, evidence=""):
        from readme_agent.capabilities import audit_package_release_surfaces, check_install_path

        monkeypatch.setattr(
            audit_package_release_surfaces, "list_releases", lambda org_repo, token: releases
        )
        monkeypatch.setattr(
            check_install_path,
            "inspect_repo",
            lambda org_repo, check_install=True: {
                "presentation_report": type(
                    "FakeReport",
                    (),
                    {
                        "install_path_resolved": install_path_resolved,
                        "evidence": {"install_path_resolved": evidence},
                    },
                )()
            },
        )

    def test_first_run_is_first_observation_and_records_state(self, tmp_path, monkeypatch):
        from readme_agent.specialists import package_release_audit

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        self._mock_network(monkeypatch, releases=[], install_path_resolved=None)
        backend = _FakeStateBackend()

        result = package_release_audit.run(ORG_REPO, backend)

        assert result.accepted_status == "FIRST_OBSERVATION"
        assert result.details["releases_count"] == 0
        assert result.details["handoff_findings"] == []
        stored = backend.load(ORG_REPO)
        assert stored.domain_states["package_release_audit"].accepted_status == "FIRST_OBSERVATION"

    def test_unresolved_install_path_produces_a_handoff_finding(self, tmp_path, monkeypatch):
        """The real, common anomaly this project's own portfolio survey
        already found: a package that never resolves against its stated
        registry -- a class-D finding, not silently dropped."""
        from readme_agent.specialists import package_release_audit

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        self._mock_network(
            monkeypatch,
            releases=[],
            install_path_resolved=False,
            evidence="Maven Central: NOT FOUND (0 results)",
        )
        backend = _FakeStateBackend()

        result = package_release_audit.run(ORG_REPO, backend)

        assert len(result.details["handoff_findings"]) == 1
        finding = result.details["handoff_findings"][0]
        assert finding["surface"] == "packages"
        assert "did not resolve" in finding["anomaly"]

    def test_resolved_install_path_produces_no_handoff_finding(self, tmp_path, monkeypatch):
        from readme_agent.specialists import package_release_audit

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        self._mock_network(monkeypatch, releases=[], install_path_resolved=True)
        backend = _FakeStateBackend()

        result = package_release_audit.run(ORG_REPO, backend)

        assert result.details["handoff_findings"] == []

    def test_second_run_with_unchanged_audit_is_no_change(self, tmp_path, monkeypatch):
        from readme_agent.specialists import package_release_audit

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        self._mock_network(monkeypatch, releases=[], install_path_resolved=None)
        backend = _FakeStateBackend()

        first = package_release_audit.run(ORG_REPO, backend)
        assert first.accepted_status == "FIRST_OBSERVATION"

        second = package_release_audit.run(ORG_REPO, backend)
        assert second.accepted_status == "NO_CHANGE"


class TestMetadataPresentationSpecialist:
    """Wave 7d: dispatches the existing, unscoped get_product_facts and the
    new, domain-scoped propose_metadata_changes. `accepted_status` stays the
    generic change/no-change verdict (never overridden to reflect "is there
    still an open proposal") -- a persistently unaddressed proposal must
    still let an otherwise-unchanged rerun converge via the supervisor's
    shortcut; the proposal itself always lives in `details` regardless."""

    def _mock_repo_summary(self, monkeypatch, *, description, homepage, topics):
        from readme_agent.capabilities import propose_metadata_changes

        monkeypatch.setattr(
            propose_metadata_changes,
            "repo_summary",
            lambda org_repo, token: {
                "description": description,
                "homepage": homepage,
                "topics": topics,
            },
        )

    def test_first_run_proposes_missing_description_and_records_state(self, tmp_path, monkeypatch):
        from readme_agent.specialists import metadata_presentation

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        self._mock_repo_summary(monkeypatch, description=None, homepage=None, topics=["java"])
        backend = _FakeStateBackend()

        result = metadata_presentation.run(ORG_REPO, backend)

        assert result.accepted_status == "FIRST_OBSERVATION"
        assert result.details["proposed_description"] == "widget FOSS library for java"
        assert result.details["has_proposal"] is True
        stored = backend.load(ORG_REPO)
        assert stored.domain_states["metadata_presentation"].accepted_status == "FIRST_OBSERVATION"

    def test_no_proposal_when_metadata_already_complete(self, tmp_path, monkeypatch):
        from readme_agent.specialists import metadata_presentation

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        self._mock_repo_summary(
            monkeypatch,
            description="Already complete",
            homepage="https://products.example.org/widget/java/",
            topics=["java"],
        )
        backend = _FakeStateBackend()

        result = metadata_presentation.run(ORG_REPO, backend)

        assert result.details["has_proposal"] is False

    def test_unaddressed_proposal_still_converges_to_no_change_on_rerun(
        self, tmp_path, monkeypatch
    ):
        """The specific correctness property: an *unaddressed* proposal
        (description still missing both runs) must not permanently block
        the supervisor's convergence shortcut -- `accepted_status` tracks
        "did anything change," not "is there still something to fix"."""
        from readme_agent.specialists import metadata_presentation

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        self._mock_repo_summary(monkeypatch, description=None, homepage=None, topics=["java"])
        backend = _FakeStateBackend()

        first = metadata_presentation.run(ORG_REPO, backend)
        assert first.accepted_status == "FIRST_OBSERVATION"
        assert first.details["has_proposal"] is True

        second = metadata_presentation.run(ORG_REPO, backend)
        assert second.accepted_status == "NO_CHANGE"
        assert second.details["has_proposal"] is True  # still visible, just not "new"


class TestCommunityFilesPresentationSpecialist:
    """Wave 7e: dispatches the new, domain-scoped audit_community_files
    capability, which does a real local clone+scan (mirrored via the same
    real-local-git-repo fixtures every other specialist test in this file
    uses) plus one mocked network call (Community Profile API)."""

    def _mock_community_profile(self, monkeypatch, *, health_percentage, files):
        from readme_agent.capabilities import audit_community_files

        monkeypatch.setattr(
            audit_community_files,
            "get_community_profile",
            lambda org_repo, token: {"health_percentage": health_percentage, "files": files},
        )

    def test_first_run_is_first_observation_and_records_state(self, tmp_path, monkeypatch):
        from readme_agent.specialists import community_files_presentation

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        self._mock_community_profile(
            monkeypatch,
            health_percentage=20,
            files={"license": None, "contributing": None, "code_of_conduct": None},
        )
        backend = _FakeStateBackend()

        result = community_files_presentation.run(ORG_REPO, backend)

        assert result.accepted_status == "FIRST_OBSERVATION"
        assert result.details["present_files"]["LICENSE"] is False
        assert "CODE_OF_CONDUCT" in result.details["prepared_candidates"]
        stored = backend.load(ORG_REPO)
        assert (
            stored.domain_states["community_files_presentation"].accepted_status
            == "FIRST_OBSERVATION"
        )

    def test_second_run_with_unchanged_audit_is_no_change(self, tmp_path, monkeypatch):
        from readme_agent.specialists import community_files_presentation

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        self._mock_community_profile(
            monkeypatch,
            health_percentage=20,
            files={"license": None, "contributing": None, "code_of_conduct": None},
        )
        backend = _FakeStateBackend()

        first = community_files_presentation.run(ORG_REPO, backend)
        assert first.accepted_status == "FIRST_OBSERVATION"

        second = community_files_presentation.run(ORG_REPO, backend)
        assert second.accepted_status == "NO_CHANGE"

    def test_prepared_candidate_fingerprint_stability_does_not_block_no_change(
        self, tmp_path, monkeypatch
    ):
        """The fingerprint deliberately excludes the constant
        prepared_candidates text -- confirms including it wouldn't have
        mattered anyway, since it never varies run to run, but the real
        protection is against a hypothetical future candidate source that
        does vary for reasons unrelated to the tracked audit signal."""
        from readme_agent.specialists import community_files_presentation

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        self._mock_community_profile(
            monkeypatch,
            health_percentage=20,
            files={"license": None, "contributing": None, "code_of_conduct": None},
        )
        backend = _FakeStateBackend()

        first = community_files_presentation.run(ORG_REPO, backend)
        second = community_files_presentation.run(ORG_REPO, backend)

        assert first.accepted_facts_hash == second.accepted_facts_hash


class TestCrossSurfaceValidationSpecialist:
    """Wave 7f: the sixth specialist, and the first with no capability of
    its own -- reads `readme_reconciliation`'s and `community_files_
    presentation`'s already-recorded `DomainStateV1.details` directly via
    `backend.load()`. Real local git repos throughout, only the Community
    Profile API network call mocked, matching this file's own convention."""

    def _mock_community_profile(self, monkeypatch, *, files):
        from readme_agent.capabilities import audit_community_files

        monkeypatch.setattr(
            audit_community_files,
            "get_community_profile",
            lambda org_repo, token: {"health_percentage": 50, "files": files},
        )

    def test_no_backend_degrades_honestly_instead_of_erroring(self):
        from readme_agent.specialists import cross_surface_validation

        result = cross_surface_validation.run(ORG_REPO, None)

        assert result.accepted_status == "FIRST_OBSERVATION"
        assert result.details["inconsistencies"] == []
        assert "no durable state backend" in result.details["note"]

    def test_no_siblings_recorded_yet_produces_no_inconsistency_not_an_error(
        self, tmp_path, monkeypatch
    ):
        """Real backend, but this domain runs before any sibling ever has --
        both facts are absent, not a crash and not a false-positive finding."""
        from readme_agent.specialists import cross_surface_validation

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()

        result = cross_surface_validation.run(ORG_REPO, backend)

        assert result.accepted_status == "FIRST_OBSERVATION"
        assert result.details["inconsistencies"] == []
        # MEM-005: neither sibling has ever successfully recorded -- both
        # named, not silently treated as "both sides agree."
        assert result.details["stale_sibling_data"] == {
            "readme_reconciliation": "no persisted state -- never successfully recorded",
            "community_files_presentation": "no persisted state -- never successfully recorded",
        }

    def test_intentionally_introduced_license_mismatch_is_detected(self, tmp_path, monkeypatch):
        """The plan's own required live-mechanism proof: a real, deliberately
        introduced mismatch between what the README claims and what the
        LICENSE file actually is must produce a real inconsistency finding,
        not a silently-passed check."""
        from readme_agent.specialists import (
            community_files_presentation,
            cross_surface_validation,
            readme_reconciliation,
        )

        source = _init_source_repo(
            tmp_path / "source", "# Widget\n\nLicensed under the MIT License.\n"
        )
        (source / "LICENSE").write_text(
            "Apache License\nVersion 2.0, January 2004\n", encoding="utf-8"
        )
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "add LICENSE"], cwd=source)
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        self._mock_community_profile(
            monkeypatch, files={"license": None, "contributing": None, "code_of_conduct": None}
        )
        backend = _FakeStateBackend()

        readme_reconciliation.run(ORG_REPO, backend)
        community_files_presentation.run(ORG_REPO, backend)
        result = cross_surface_validation.run(ORG_REPO, backend)

        assert len(result.details["inconsistencies"]) == 1
        finding = result.details["inconsistencies"][0]
        assert finding["surface"] == "license"
        assert finding["evidence"]["readme_reconciliation_license_claim"] == "MIT"
        assert finding["evidence"]["community_files_presentation_detected_license"] == "Apache-2.0"

    def test_agreeing_facts_produce_no_inconsistency(self, tmp_path, monkeypatch):
        from readme_agent.specialists import (
            community_files_presentation,
            cross_surface_validation,
            readme_reconciliation,
        )

        source = _init_source_repo(
            tmp_path / "source", "# Widget\n\nLicensed under the MIT License.\n"
        )
        (source / "LICENSE").write_text("MIT License\n", encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "add LICENSE"], cwd=source)
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        self._mock_community_profile(
            monkeypatch, files={"license": None, "contributing": None, "code_of_conduct": None}
        )
        backend = _FakeStateBackend()

        readme_reconciliation.run(ORG_REPO, backend)
        community_files_presentation.run(ORG_REPO, backend)
        result = cross_surface_validation.run(ORG_REPO, backend)

        assert result.details["inconsistencies"] == []
        # MEM-005: both siblings genuinely recorded this pass -- nothing stale.
        assert result.details["stale_sibling_data"] == {}

    def test_second_run_with_unchanged_facts_is_no_change(self, tmp_path, monkeypatch):
        from readme_agent.specialists import (
            community_files_presentation,
            cross_surface_validation,
            readme_reconciliation,
        )

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        self._mock_community_profile(
            monkeypatch, files={"license": None, "contributing": None, "code_of_conduct": None}
        )
        backend = _FakeStateBackend()

        readme_reconciliation.run(ORG_REPO, backend)
        community_files_presentation.run(ORG_REPO, backend)
        first = cross_surface_validation.run(ORG_REPO, backend)
        assert first.accepted_status == "FIRST_OBSERVATION"

        readme_reconciliation.run(ORG_REPO, backend)
        community_files_presentation.run(ORG_REPO, backend)
        second = cross_surface_validation.run(ORG_REPO, backend)
        assert second.accepted_status == "NO_CHANGE"


# Phase 21: the product_first_opening/commercial_mention_discipline
# validation rules require the opening to explain the product (>= 8 words,
# a concrete phrase) before any commercial link -- mirrors
# test_orchestrator.py's own proven-valid BLANK_SLATE_README exactly, product
# name substituted, so a real GENERATED status (not BLOCKED_VALIDATION_
# FAILED) is reachable for the tests that need to prove a real commit.
_BLANK_SLATE_WIDGET_README = (
    "# Example Widget\n\n"
    "Example Widget is a Java library for creating, reading, and modifying widget files.\n"
)


class TestReadmePresentationSpecialist:
    """Wave 7g (extended Wave 8b): the one real mutating capability,
    exercised through the actual four-node graph (render -> verify -> commit
    -> record) against a real local git repo -- the only network-adjacent
    thing faked is the one LLM call `render_readme_candidate`'s underlying
    pipeline needs for this fixture's real gap (relationship_explained)."""

    def test_a_genuinely_invalid_render_is_rejected_and_never_committed(
        self, tmp_path, monkeypatch
    ):
        """Wave 8b's own concrete regression target: `"# Widget\\n\\nA
        widget library.\\n"` is a real, already-known-invalid fixture (see
        `_BLANK_SLATE_WIDGET_README`'s own comment above) whose real render
        produces a genuine `BLOCKED_VALIDATION_FAILED` status -- before this
        wave, `_commit_node` durably accepted this unconditionally (the
        found defect). Now the independent verifier must reject it, and the
        write/commit must never happen at all -- no mocking, the actual
        rendering and validation pipeline runs for real."""
        from readme_agent.specialists import readme_presentation

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))  # mode: "full"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(candidate_pipeline, "LiveLLMClient", _FakeLiveLLMClient)
        monkeypatch.setattr(
            verify_prose_quality, "LiveForcedToolClient", _FakeNonFlaggingForcedToolClient
        )
        backend = _FakeStateBackend()
        before_log = run_git(["log", "--oneline"], cwd=source).stdout

        result = readme_presentation.run(ORG_REPO, backend)

        assert result.accepted_status.startswith("ERROR:verification_rejected:")
        # _commit_node's own top-of-function guard returns {} immediately --
        # no write/commit keys, because commit_readme_write was never dispatched.
        assert "written" not in result.details
        assert "committed" not in result.details
        # No new commit landed in the work clone.
        from readme_agent import paths

        work_path = paths.work_dir("example-foss", "Example-Widget")
        after_log = run_git(["log", "--oneline"], cwd=work_path).stdout
        assert after_log.strip() == before_log.strip()
        # Wave 8d: the last-good accepted baseline is still never poisoned by
        # a rejected candidate (accepted_facts_hash stays None -- there was
        # no prior good baseline yet), but the failure IS now durably tracked
        # (save_domain_with_failure_tracking(), unlike the plain save_domain()
        # guard-and-skip every other specialist still uses).
        stored = backend.load(ORG_REPO)
        assert stored.domain_states["readme_presentation"].accepted_facts_hash is None
        assert stored.domain_states["readme_presentation"].consecutive_failure_count == 1
        assert stored.domain_states["readme_presentation"].last_failure_reason == (
            "verification_rejected"
        )

    def test_repeated_identical_rejection_increments_the_failure_counter(
        self, tmp_path, monkeypatch
    ):
        """Wave 8d (`VER-002`/"repair loops"): the concrete mechanism that
        distinguishes "this failed once" from "this has failed identically
        N times in a row and nothing is fixing it" -- two consecutive runs
        against the identical, still-invalid fixture must show the counter
        actually incrementing, not just landing at 1 once."""
        from readme_agent.specialists import readme_presentation

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(candidate_pipeline, "LiveLLMClient", _FakeLiveLLMClient)
        monkeypatch.setattr(
            verify_prose_quality, "LiveForcedToolClient", _FakeNonFlaggingForcedToolClient
        )
        backend = _FakeStateBackend()

        readme_presentation.run(ORG_REPO, backend)
        first = backend.load(ORG_REPO).domain_states["readme_presentation"]
        assert first.consecutive_failure_count == 1

        readme_presentation.run(ORG_REPO, backend)
        second = backend.load(ORG_REPO).domain_states["readme_presentation"]
        assert second.consecutive_failure_count == 2
        assert second.last_failure_reason == first.last_failure_reason

    def test_a_success_after_failures_resets_the_counter(self, tmp_path, monkeypatch):
        from readme_agent import paths
        from readme_agent.gitsafety.clone import force_rmtree
        from readme_agent.specialists import readme_presentation

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))  # mode: "full"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(candidate_pipeline, "LiveLLMClient", _FakeLiveLLMClient)
        monkeypatch.setattr(
            verify_prose_quality, "LiveForcedToolClient", _FakeNonFlaggingForcedToolClient
        )
        backend = _FakeStateBackend()

        readme_presentation.run(ORG_REPO, backend)
        first = backend.load(ORG_REPO).domain_states["readme_presentation"]
        assert first.consecutive_failure_count == 1

        # Fix the fixture -- the second run's render is now genuinely valid.
        (source / "README.md").write_text(_BLANK_SLATE_WIDGET_README, encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "fix: real body"], cwd=source)
        force_rmtree(paths.work_dir("example-foss", "Example-Widget"))
        # Simulates the process boundary supervise_repo() gets for free via its
        # own invalidate_baseline_clone() call -- see this file's own
        # _clean_clone_memo fixture docstring for why a direct, in-process
        # second run() call needs this too.
        reset_clone_memo()

        readme_presentation.run(ORG_REPO, backend)
        second = backend.load(ORG_REPO).domain_states["readme_presentation"]
        assert second.consecutive_failure_count == 0
        assert second.last_failure_reason is None

    def test_mode_full_writes_and_commits_for_real(self, tmp_path, monkeypatch):
        from readme_agent.specialists import readme_presentation

        source = _init_source_repo(tmp_path / "source", _BLANK_SLATE_WIDGET_README)
        _setup_project_root(tmp_path, str(source))  # mode: "full"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(candidate_pipeline, "LiveLLMClient", _FakeLiveLLMClient)
        monkeypatch.setattr(
            verify_prose_quality, "LiveForcedToolClient", _FakeNonFlaggingForcedToolClient
        )
        backend = _FakeStateBackend()

        result = readme_presentation.run(ORG_REPO, backend)

        assert result.accepted_status == "FIRST_OBSERVATION"
        assert result.details["written"] is True
        assert result.details["committed"] is True
        stored = backend.load(ORG_REPO)
        assert stored.domain_states["readme_presentation"].accepted_status == "FIRST_OBSERVATION"
        # ORC-004: the flat accepted-state ledger is unified with the CLI
        # path's own, not a second competing writer.
        assert stored.accepted_facts_hash == result.accepted_facts_hash
        # Wave 8b regression: `render_result` (the full candidate text) must
        # never survive into the durably-persisted record -- `_verify_node`'s
        # own `merge_details()` call preserves it so `_commit_node` can still
        # read it, but `_commit_node` must explicitly drop it before merging
        # forward, the same way the pre-Wave-8 bare-dict-return style used to
        # (accidentally) achieve by fully replacing `details` every node.
        assert "render_result" not in result.details
        assert "render_result" not in stored.domain_states["readme_presentation"].details

    def test_fresh_work_clone_does_not_re_call_the_llm_when_durable_state_agrees(
        self, tmp_path, monkeypatch
    ):
        """Production-reliability regression (found by independent review,
        2026-07-20): a persistent `work_dir` is NOT the normal case on an
        ephemeral CI runner (`RUN-001`) -- deleting it here before the second
        `run()` call simulates exactly that. Before the fix, `_render_node`
        never supplied this domain's own prior accepted state to
        `render_readme_candidate`, so a fresh clone always re-triggered the
        real LLM call and a fresh `needs_write=True`/commit attempt, on
        every single run with any upstream commit -- not just one touching
        tracked content. After the fix, the durable record alone (no local
        memory at all) is enough to skip both."""
        from readme_agent import paths
        from readme_agent.gitsafety.clone import force_rmtree
        from readme_agent.specialists import readme_presentation

        source = _init_source_repo(tmp_path / "source", _BLANK_SLATE_WIDGET_README)
        _setup_project_root(tmp_path, str(source))  # mode: "full"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(candidate_pipeline, "LiveLLMClient", _FakeLiveLLMClient)
        monkeypatch.setattr(
            verify_prose_quality, "LiveForcedToolClient", _FakeNonFlaggingForcedToolClient
        )
        backend = _FakeStateBackend()

        first = readme_presentation.run(ORG_REPO, backend)
        assert first.accepted_status == "FIRST_OBSERVATION"
        assert first.details["llm_called"] is True
        assert first.details["committed"] is True

        # Simulate an ephemeral CI runner: the persistent local work clone
        # from the first run is gone, but the durable backend (this
        # project's own remote, in real use) survives.
        work_path = paths.work_dir("example-foss", "Example-Widget")
        assert work_path.exists()  # sanity: the first run really did create one
        force_rmtree(work_path)

        second = readme_presentation.run(ORG_REPO, backend)

        assert second.accepted_status == "NO_CHANGE"
        assert second.details["llm_called"] is False
        assert second.details["written"] is False
        assert second.details["committed"] is False

        # The fresh clone is built from baseline, which never saw the first
        # run's never-pushed commit (by design -- that commit only ever
        # existed in the deleted work clone) -- so it starts back at just
        # the source repo's own "initial" commit. The real assertion is that
        # the SECOND run added nothing on top of that: no new commit either.
        log = run_git(["log", "--oneline"], cwd=work_path)
        commit_lines = [line for line in log.stdout.splitlines() if line.strip()]
        assert len(commit_lines) == 1

    def test_mode_dry_run_writes_but_never_commits(self, tmp_path, monkeypatch):
        from readme_agent.specialists import readme_presentation

        source = _init_source_repo(tmp_path / "source", _BLANK_SLATE_WIDGET_README)
        _setup_project_root(tmp_path, str(source))  # mode: "full"
        products_path = tmp_path / "data" / "products.json"
        products = json.loads(products_path.read_text(encoding="utf-8"))
        products[0]["mode"] = "dry_run"
        products_path.write_text(json.dumps(products), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(candidate_pipeline, "LiveLLMClient", _FakeLiveLLMClient)
        monkeypatch.setattr(
            verify_prose_quality, "LiveForcedToolClient", _FakeNonFlaggingForcedToolClient
        )
        backend = _FakeStateBackend()

        result = readme_presentation.run(ORG_REPO, backend)

        assert result.details["written"] is True
        assert result.details["committed"] is False

    def test_no_backend_refuses_to_dispatch_mutating_capability(self, tmp_path, monkeypatch):
        """Safety default: without a real durable backend there is no
        idempotency ledger, so this specialist refuses to attempt the
        mutating dispatch at all rather than mutate unsafely -- an honest
        degrade (a clear note), never a crash and never an unsafe write."""
        from readme_agent.specialists import readme_presentation

        source = _init_source_repo(tmp_path / "source", _BLANK_SLATE_WIDGET_README)
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(candidate_pipeline, "LiveLLMClient", _FakeLiveLLMClient)
        monkeypatch.setattr(
            verify_prose_quality, "LiveForcedToolClient", _FakeNonFlaggingForcedToolClient
        )

        result = readme_presentation.run(ORG_REPO, None)

        assert result.details["written"] is False
        assert result.details["committed"] is False
        assert "no durable state backend" in result.details["note"]

    def test_second_run_with_unchanged_content_is_no_change(self, tmp_path, monkeypatch):
        from readme_agent.specialists import readme_presentation

        source = _init_source_repo(tmp_path / "source", _BLANK_SLATE_WIDGET_README)
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(candidate_pipeline, "LiveLLMClient", _FakeLiveLLMClient)
        monkeypatch.setattr(
            verify_prose_quality, "LiveForcedToolClient", _FakeNonFlaggingForcedToolClient
        )
        backend = _FakeStateBackend()

        first = readme_presentation.run(ORG_REPO, backend)
        assert first.accepted_status == "FIRST_OBSERVATION"
        assert first.details["written"] is True

        second = readme_presentation.run(ORG_REPO, backend)

        assert second.accepted_status == "NO_CHANGE"
        assert second.details["written"] is False


class TestVisualPreparationSpecialist:
    """Wave 7h: the eighth specialist, prepare-only -- dispatches the
    existing unscoped get_product_facts then the new, domain-scoped
    prepare_visual_asset. No network, no write, real local git repos
    throughout (no image asset in this fixture repo, so this exercises the
    real freshly-generated-candidate path via real Pillow calls). "No
    network" requires forcing env.gh_token() to None below -- get_product_
    facts' profiling path otherwise takes a real GitHub-API branch whenever
    a real GH_TOKEN/GITHUB_PAT happens to be set in the environment (SCL-004,
    decision #40/Part F), intermittently hanging at DNS/connect against this
    fixture's fake org_repo (found live, 2026-07-21, `OPS-010`) -- the same
    fix `test_profile_cached.py` already established for the identical
    problem."""

    def test_first_run_prepares_a_candidate_and_records_state(self, tmp_path, monkeypatch):
        from readme_agent.specialists import visual_preparation

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(cached.env, "gh_token", lambda: None)
        monkeypatch.setattr(
            review_visual_asset_accuracy, "LiveAnalysisClient", _FakeNonFlaggingAnalysisClient
        )
        backend = _FakeStateBackend()

        result = visual_preparation.run(ORG_REPO, backend)

        assert result.accepted_status == "FIRST_OBSERVATION"
        assert result.details["existing_asset_found"] is False
        assert result.details["prepared_candidate"]["filename"] == "banner.png"
        stored = backend.load(ORG_REPO)
        assert stored.domain_states["visual_preparation"].accepted_status == "FIRST_OBSERVATION"

    def test_second_run_with_unchanged_facts_is_no_change(self, tmp_path, monkeypatch):
        from readme_agent.specialists import visual_preparation

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(cached.env, "gh_token", lambda: None)
        monkeypatch.setattr(
            review_visual_asset_accuracy, "LiveAnalysisClient", _FakeNonFlaggingAnalysisClient
        )
        backend = _FakeStateBackend()

        first = visual_preparation.run(ORG_REPO, backend)
        assert first.accepted_status == "FIRST_OBSERVATION"

        second = visual_preparation.run(ORG_REPO, backend)
        assert second.accepted_status == "NO_CHANGE"


class TestIndependentVerificationSpecialist:
    """Wave 8b: the ninth specialist, the post-hoc facet of `VER-001`'s
    two-facet design -- evidence-completeness only this sub-wave (8c extends
    it). No capability of its own; reads sibling `DomainStateV1` state the
    same way `cross_surface_validation` already does."""

    def test_no_backend_degrades_honestly_instead_of_erroring(self):
        from readme_agent.specialists import independent_verification

        result = independent_verification.run(ORG_REPO, None)

        assert result.accepted_status == "FIRST_OBSERVATION"
        assert result.details["checks_performed"] == [
            "evidence_completeness",
            "requirement_mapping",
            "adversarial_cross_domain",
        ]
        assert result.details["completeness"] == {}
        assert "no durable state backend" in result.details["note"]

    def test_no_siblings_recorded_yet_produces_no_completeness_issue(self, tmp_path, monkeypatch):
        from readme_agent.specialists import independent_verification

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()

        result = independent_verification.run(ORG_REPO, backend)

        assert result.accepted_status == "FIRST_OBSERVATION"
        assert result.details["checks_performed"] == [
            "evidence_completeness",
            "requirement_mapping",
            "adversarial_cross_domain",
        ]
        assert result.details["completeness"] == {}

    def test_a_sibling_missing_its_expected_detail_keys_is_flagged(self, tmp_path, monkeypatch):
        from readme_agent.specialists import independent_verification

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()
        # Seed a sibling with a real, non-ERROR status but incomplete details
        # -- exactly the condition this domain's evidence-completeness check
        # exists to catch.
        backend._states[ORG_REPO] = RunStateV1(
            org_repo=ORG_REPO,
            domain_states={
                "readme_reconciliation": DomainStateV1(
                    domain="readme_reconciliation", accepted_status="NO_CHANGE", details={}
                )
            },
        )

        result = independent_verification.run(ORG_REPO, backend)

        assert result.details["completeness"]["readme_reconciliation"] == ["license_claim"]

    def test_a_sibling_with_complete_details_is_not_flagged(self, tmp_path, monkeypatch):
        from readme_agent.specialists import independent_verification

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()
        backend._states[ORG_REPO] = RunStateV1(
            org_repo=ORG_REPO,
            domain_states={
                "readme_reconciliation": DomainStateV1(
                    domain="readme_reconciliation",
                    accepted_status="NO_CHANGE",
                    details={"license_claim": "MIT"},
                )
            },
        )

        result = independent_verification.run(ORG_REPO, backend)

        assert "readme_reconciliation" not in result.details["completeness"]

    def test_requirement_map_reports_exercised_capabilities(self, tmp_path, monkeypatch):
        """Wave 8c: a coarse, honest 'was the evidence-producing capability
        exercised and did it succeed' -- `classify_upstream_change` is
        domain-scoped to `readme_reconciliation`, an unambiguous attribution."""
        from readme_agent.specialists import independent_verification

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()
        backend._states[ORG_REPO] = RunStateV1(
            org_repo=ORG_REPO,
            domain_states={
                "readme_reconciliation": DomainStateV1(
                    domain="readme_reconciliation",
                    accepted_status="NO_CHANGE",
                    details={"license_claim": "MIT"},
                )
            },
        )

        result = independent_verification.run(ORG_REPO, backend)

        assert result.details["requirement_map"]["CAP-006"] == {
            "domain": "readme_reconciliation",
            "capability_id": "classify_upstream_change",
            "exercised_without_error": True,
        }

    def test_requirement_map_reports_error_status_as_not_exercised(self, tmp_path, monkeypatch):
        from readme_agent.specialists import independent_verification

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()
        backend._states[ORG_REPO] = RunStateV1(
            org_repo=ORG_REPO,
            domain_states={
                "readme_reconciliation": DomainStateV1(
                    domain="readme_reconciliation",
                    accepted_status="ERROR:execution_error:boom",
                    details={},
                )
            },
        )

        result = independent_verification.run(ORG_REPO, backend)

        assert result.details["requirement_map"]["CAP-006"]["exercised_without_error"] is False

    def test_adversarial_finding_when_committed_despite_unresolved_inconsistency(
        self, tmp_path, monkeypatch
    ):
        """Wave 8c: the second-order check on top of `cross_surface_
        validation`'s own first-order `inconsistencies` list."""
        from readme_agent.specialists import independent_verification

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()
        backend._states[ORG_REPO] = RunStateV1(
            org_repo=ORG_REPO,
            domain_states={
                "cross_surface_validation": DomainStateV1(
                    domain="cross_surface_validation",
                    accepted_status="NO_CHANGE",
                    details={
                        "inconsistencies": [{"surface": "license", "description": "mismatch"}]
                    },
                ),
                "readme_presentation": DomainStateV1(
                    domain="readme_presentation",
                    accepted_status="NO_CHANGE",
                    details={"committed": True},
                ),
            },
        )

        result = independent_verification.run(ORG_REPO, backend)

        assert len(result.details["adversarial_findings"]) == 1
        assert "committed" in result.details["adversarial_findings"][0]["finding"]

    def test_no_adversarial_finding_when_nothing_was_committed(self, tmp_path, monkeypatch):
        from readme_agent.specialists import independent_verification

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()
        backend._states[ORG_REPO] = RunStateV1(
            org_repo=ORG_REPO,
            domain_states={
                "cross_surface_validation": DomainStateV1(
                    domain="cross_surface_validation",
                    accepted_status="NO_CHANGE",
                    details={
                        "inconsistencies": [{"surface": "license", "description": "mismatch"}]
                    },
                ),
                "readme_presentation": DomainStateV1(
                    domain="readme_presentation",
                    accepted_status="NO_CHANGE",
                    details={"committed": False},
                ),
            },
        )

        result = independent_verification.run(ORG_REPO, backend)

        assert result.details["adversarial_findings"] == []

    def test_failure_escalation_visibility_surfaces_sibling_counters(self, tmp_path, monkeypatch):
        from readme_agent.specialists import independent_verification

        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()
        backend._states[ORG_REPO] = RunStateV1(
            org_repo=ORG_REPO,
            domain_states={
                "readme_reconciliation": DomainStateV1(
                    domain="readme_reconciliation",
                    accepted_status="ERROR:execution_error:boom",
                    details={},
                    consecutive_failure_count=3,
                    last_failure_reason="execution_error",
                )
            },
        )

        result = independent_verification.run(ORG_REPO, backend)

        assert result.details["failure_escalations"]["readme_reconciliation"] == {
            "consecutive_failure_count": 3,
            "last_failure_reason": "execution_error",
        }
