"""End-to-end control-flow proof against synthetic local git repos -- no
network, no real secrets. Mirrors the three real pilot states found in the
2026-07-17 README audit: blank-slate (cells/java), fully-compliant (3d/java),
partial-gap (pdf/java).
"""

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from readme_agent import orchestrator, paths
from readme_agent.errors import NotAllowlistedError, StateBackendError
from readme_agent.gitsafety._git import run_git
from readme_agent.orchestrator import (
    generate_repo,
    profile_repo_with_cache,
    run_registry,
    run_registry_profiling_sweep,
    run_repo,
)
from readme_agent.profile.schema import RepositoryProfile
from readme_agent.readme.markers import render_span
from readme_agent.state.backend import SaveResult
from readme_agent.state.schema import DomainStateV1, ProfileCacheV1, RunStateV1, SupervisorStateV1

REPO_ROOT = Path(__file__).resolve().parents[2]

# Phase 21: must explain the product (not just name it) so the new
# product_first_opening/commercial_mention_discipline gates pass cleanly on
# fixtures that aren't testing those rules specifically.
BLANK_SLATE_README = (
    "# Example FOSS for Java\n\n"
    "Example FOSS for Java is a Java library for creating, reading, and "
    "modifying document files.\n"
)

POM_XML = """<project>
  <groupId>com.example</groupId>
  <artifactId>example-foss</artifactId>
  <version>1.0.0</version>
  <name>Example FOSS</name>
</project>
"""

FIXTURE_RESPONSE = {
    "relationship_paragraph": (
        "This repository is the free, open-source FOSS edition of the "
        "corresponding commercial Example product. Upgrade to the commercial "
        "edition when you need a broader feature set or dedicated support."
    ),
    "talking_points_covered": ["open_source_scope", "commercial_upgrade_path"],
    "claims": {
        "license_name": "MIT",
        "commercial_link_url": "https://products.example.com/thing/java/",
    },
}

POLICY_YAML = """schema_version: 2
policy_profile: test-profile
required_elements:
  license_mentioned:
    detected_license: MIT
  products_org_link:
    url: "https://products.example.org/thing/java/"
    family_url: "https://products.example.org/thing/"
    label: "Example FOSS for Java"
  products_com_link:
    url: "https://products.example.com/thing/java/"
    family_url: "https://products.example.com/thing"
    label: "Example for Java"
  relationship_explained:
    min_sentences: 2
    talking_points: [open_source_scope, commercial_upgrade_path]
secondary_links: []
block:
  word_limit: { min: 10, max: 200 }
  prohibited_terms: ["guarantee"]
  link_whitelist_domains: [products.example.com, products.example.org]
"""


def _init_source_repo(path, readme_text: str):
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-b", "main"], cwd=path)
    run_git(["config", "user.email", "test@example.com"], cwd=path)
    run_git(["config", "user.name", "Test"], cwd=path)
    (path / "README.md").write_text(readme_text, encoding="utf-8")
    (path / "pom.xml").write_text(POM_XML, encoding="utf-8")
    (path / "LICENSE").write_text(
        "MIT License\n\nPermission is hereby granted...", encoding="utf-8"
    )
    run_git(["add", "."], cwd=path)
    run_git(["commit", "-m", "initial"], cwd=path)
    return path


def _setup_project_root(tmp_path, source_clone_url: str, mode: str):
    (tmp_path / "data").mkdir()
    (tmp_path / "config" / "policies").mkdir(parents=True)
    # Wave 8.5: llm.prompts.prompt_content_hash() reads
    # prompts/generation/relationship_explained.yaml fresh, cwd-relative, on
    # every call -- staged here so it doesn't raise after monkeypatch.chdir().
    # build_prompt() itself reads from the eagerly import-time-cached
    # prompt_registry instead, unaffected by cwd.
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
            "family": "thing",
            "platform": "java",
            "repo_name": "Example-FOSS-for-Java",
            "repo_url": "https://github.com/example-foss/Example-FOSS-for-Java",
            "clone_url": source_clone_url,
            "active": True,
            "discovered_via": "manual",
            "mode": mode,
            "ecosystem": "java",
            "policy_profile": "test-profile",
        }
    ]
    (tmp_path / "data" / "products.json").write_text(json.dumps(products), encoding="utf-8")
    (tmp_path / "config" / "policies" / "test-profile.yml").write_text(
        POLICY_YAML, encoding="utf-8"
    )
    fixture_path = tmp_path / "fixture_response.json"
    fixture_path.write_text(json.dumps(FIXTURE_RESPONSE), encoding="utf-8")
    return fixture_path


ORG_REPO = "example-foss/Example-FOSS-for-Java"


class _FakeStateBackend:
    """Minimal in-memory `StateBackend` for the fresh-runner test below --
    the full CAS/lock contract is proven separately (test_state_backend.py),
    this one only needs `load`/`save` to seed an accepted record."""

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
        return None

    def release_lock(self, lock):
        pass

    def lock_still_held(self, lock):
        return True


class _RaisingStateBackend:
    """A `StateBackend` whose every method raises `StateBackendError` --
    simulates a durable backend that is unreachable (network, credentials --
    the exact failure `RUN-003`'s live `act` reproduction found: a checkout
    that didn't persist push credentials made a real `git push` fail this
    way). Proves the opt-in enhancement can never take down the run it's
    enhancing, mirroring `inspect_repo`'s `check_install` convention."""

    def load(self, org_repo):
        raise StateBackendError("simulated: durable backend unreachable (load)")

    def save(self, org_repo, state, expected_version):
        raise StateBackendError("simulated: durable backend unreachable (save)")

    def acquire_lock(self, org_repo):
        raise StateBackendError("simulated: durable backend unreachable (lock)")

    def release_lock(self, lock):
        raise StateBackendError("simulated: durable backend unreachable (lock)")

    def lock_still_held(self, lock):
        raise StateBackendError("simulated: durable backend unreachable (lock)")


class TestBlankSlateRepo:
    """Mirrors cells/java: nothing present, needs a real LLM call."""

    def test_first_run_generates_and_calls_the_llm(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        result = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)

        assert result.status == "GENERATED"
        assert result.llm_called
        assert result.llm_calls == ["relationship_explained"]
        text = result.work_readme_path.read_text(encoding="utf-8")
        assert "products.example.org" in text
        assert "products.example.com" in text
        assert "free, open-source FOSS edition" in text

        # LLM-015: usage must be visible in evidence, not just minimized.
        manifest = json.loads((result.evidence_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["llm_call_count"] == 1
        assert manifest["llm_calls"] == ["relationship_explained"]

    def test_second_run_is_idempotent_zero_llm_calls(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        first = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)
        assert first.llm_called

        second = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)

        assert second.status == "COMPLIANT_NO_CHANGE"
        assert not second.llm_called
        assert second.work_readme_path.read_text(
            encoding="utf-8"
        ) == first.work_readme_path.read_text(encoding="utf-8")


class TestFullyCompliantRepo:
    """Mirrors 3d/java: already hand-authored, must take zero action."""

    def test_zero_gaps_produces_zero_changes_zero_llm_calls(self, tmp_path, monkeypatch):
        compliant_readme = (
            "# Example FOSS for Java\n\n"
            "MIT License. This is the free, open-source edition. "
            "Upgrade to the commercial edition for a broader feature set.\n\n"
            "https://products.example.org/thing/java/\n"
            "https://products.example.com/thing/java/\n"
        )
        source = _init_source_repo(tmp_path / "source", compliant_readme)
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        result = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)

        assert result.status == "COMPLIANT_NO_CHANGE"
        assert not result.llm_called
        assert result.llm_calls == []
        assert result.gap_report.fully_compliant
        # Never touched: file on disk still equals what was originally cloned.
        assert result.work_readme_path.read_text(encoding="utf-8") == compliant_readme


class TestCalloutMigration:
    """RDM-001 / decision #9: a legacy callout span already materialized in a
    work clone (from before Phase 21) must be stripped on the very next run,
    even when that run is otherwise a no-op skip -- generate_repo's skip
    branch never writes readme_path, so this proves the migration step's
    unconditional, always-persisted write (orchestrator.py, right after
    current_text is read) actually reaches disk rather than only existing
    in memory for that one run."""

    def test_legacy_callout_left_in_a_work_clone_is_stripped_on_next_run(
        self, tmp_path, monkeypatch
    ):
        compliant_readme = (
            "# Example FOSS for Java\n\n"
            "MIT License. This is the free, open-source edition. "
            "Upgrade to the commercial edition for a broader feature set.\n\n"
            "https://products.example.org/thing/java/\n"
            "https://products.example.com/thing/java/\n"
        )
        source = _init_source_repo(tmp_path / "source", compliant_readme)
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        first = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)
        assert first.status == "COMPLIANT_NO_CHANGE"

        # Simulate a pre-Phase-21 work clone by appending a legacy callout
        # span directly to the on-disk work clone -- bypassing upsert_span,
        # which no longer accepts "callout" (see markers.py).
        work_readme_path = paths.work_dir("example-foss", "Example-FOSS-for-Java") / "README.md"
        legacy_span = render_span("callout", "old promotional banner", "deadbeef")
        work_readme_path.write_text(compliant_readme + "\n" + legacy_span, encoding="utf-8")

        second = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)

        assert second.status == "COMPLIANT_NO_CHANGE"
        assert not second.llm_called
        final_text = second.work_readme_path.read_text(encoding="utf-8")
        assert "readme-agent:callout" not in final_text
        assert final_text == compliant_readme


class TestPartialGapRepo:
    """Mirrors pdf/java: has the commercial link + relationship prose, missing
    only the org link -- the entire fix must be deterministic, zero LLM calls."""

    def test_missing_only_org_link_fixes_without_calling_the_llm(self, tmp_path, monkeypatch):
        half_done_readme = (
            "# Example FOSS for Java\n\n"
            "MIT License. This is a commercial-grade project with a full "
            "upgrade path to the paid edition.\n\n"
            "https://products.example.com/thing/java/\n"
        )
        source = _init_source_repo(tmp_path / "source", half_done_readme)
        fixture_path = _setup_project_root(tmp_path, str(source), mode="dry_run")
        monkeypatch.chdir(tmp_path)

        result = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)

        assert result.status == "GENERATED"
        assert not result.llm_called
        text = result.work_readme_path.read_text(encoding="utf-8")
        assert "products.example.org" in text


class TestAllowList:
    def test_repo_not_in_products_json_is_rejected(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# X\n")
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(NotAllowlistedError):
            generate_repo(
                "some-org/not-listed", llm_mode="fixture", fixture_response_path=fixture_path
            )

    def test_disabled_mode_is_rejected(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# X\n")
        fixture_path = _setup_project_root(tmp_path, str(source), mode="disabled")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(NotAllowlistedError):
            generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)


class TestLegacyRunIsReadOnlyCompatibility:
    def test_full_mode_never_commits_outside_registered_effect(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        result = run_repo(
            ORG_REPO, mode="full", llm_mode="fixture", fixture_response_path=fixture_path
        )

        assert result.ok
        assert result.status == "GENERATED"
        assert not result.committed
        assert result.push_block_ok


class TestRunRegistryBaselineCleanup:
    """Decision #40/Part B: a registry-wide loop over several repos must not
    accumulate every one of their baseline clones on disk for the rest of
    the batch -- run_registry() cleans up each entry's baseline dir once
    that entry's run is done, success or failure."""

    def test_baseline_dir_is_removed_after_run_registry_processes_entry(
        self, tmp_path, monkeypatch
    ):
        # Fully compliant (zero gaps, mirrors TestFullyCompliantRepo above) so
        # generate_repo() never reaches the LLM-call branch at all --
        # run_registry() has no llm_mode passthrough, so a gapped README here
        # would attempt a real live LLM call.
        compliant_readme = (
            "# Example FOSS for Java\n\n"
            "MIT License. This is the free, open-source edition. "
            "Upgrade to the commercial edition for a broader feature set.\n\n"
            "https://products.example.org/thing/java/\n"
            "https://products.example.com/thing/java/\n"
        )
        source = _init_source_repo(tmp_path / "source", compliant_readme)
        _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        results = run_registry()

        assert len(results) == 1
        assert results[0].ok
        baseline_path = paths.baseline_dir("example-foss", "Example-FOSS-for-Java")
        assert not baseline_path.exists()

    def test_baseline_dir_is_removed_even_when_the_entry_errors(self, tmp_path, monkeypatch):
        """The cleanup lives in a `finally`, not just the success path --
        proven here by seeding a products.json entry whose clone_url is
        simply wrong, so run_repo() raises before ever finishing."""
        (tmp_path / "data").mkdir()
        products = [
            {
                "family": "thing",
                "platform": "java",
                "repo_name": "Example-FOSS-for-Java",
                "repo_url": "https://github.com/example-foss/Example-FOSS-for-Java",
                "clone_url": str(tmp_path / "does-not-exist"),
                "active": True,
                "discovered_via": "manual",
                "mode": "full",
                "ecosystem": "java",
                "policy_profile": "test-profile",
            }
        ]
        (tmp_path / "data" / "products.json").write_text(json.dumps(products), encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        results = run_registry()

        assert len(results) == 1
        assert not results[0].ok
        baseline_path = paths.baseline_dir("example-foss", "Example-FOSS-for-Java")
        assert not baseline_path.exists()


def _fake_product_entry(org_repo="acme/widget"):
    org, repo_name = org_repo.split("/", 1)
    return SimpleNamespace(
        org=org,
        repo_name=repo_name,
        org_repo=org_repo,
        clone_url=f"https://example.invalid/{org_repo}.git",
    )


class TestProfileRepoWithCache:
    """Decision #40, Part E: the deterministic-wiring counterpart to the
    now-stateless profile.cached.get_or_build_profile() -- owns loading
    prior state before the call and CAS-writing the fresh result back after
    it. get_or_build_profile()/remote_head_sha() are monkeypatched at the
    orchestrator module level so this stays a fast, offline unit test."""

    def test_no_backend_passes_no_prior_values(self, monkeypatch):
        entry = _fake_product_entry()
        fresh_profile = RepositoryProfile(
            org_repo=entry.org_repo, detected_ecosystems=[], unresolved_manifests=[]
        )
        captured = {}

        def _fake_get_or_build_profile(entry, **kwargs):
            captured.update(kwargs)
            return fresh_profile

        monkeypatch.setattr(orchestrator, "get_or_build_profile", _fake_get_or_build_profile)

        result = profile_repo_with_cache(entry, None)

        assert result == fresh_profile
        assert captured == {"prior_upstream_revision": None, "prior_profile_result": None}

    def test_loads_prior_cache_and_passes_it_through(self, monkeypatch):
        entry = _fake_product_entry()
        prior_profile_result = RepositoryProfile(
            org_repo=entry.org_repo, detected_ecosystems=[], unresolved_manifests=["old.toml"]
        ).model_dump(mode="json")
        backend = _FakeStateBackend()
        backend.save(
            entry.org_repo,
            RunStateV1(
                org_repo=entry.org_repo,
                profile_cache=ProfileCacheV1(
                    upstream_revision="old-sha", profile_result=prior_profile_result
                ),
            ),
            expected_version=None,
        )
        captured = {}

        def _fake_get_or_build_profile(entry, **kwargs):
            captured.update(kwargs)
            return RepositoryProfile(
                org_repo=entry.org_repo, detected_ecosystems=[], unresolved_manifests=[]
            )

        monkeypatch.setattr(orchestrator, "get_or_build_profile", _fake_get_or_build_profile)
        monkeypatch.setattr(orchestrator, "remote_head_sha", lambda clone_url: "new-sha")

        profile_repo_with_cache(entry, backend)

        assert captured["prior_upstream_revision"] == "old-sha"
        assert captured["prior_profile_result"] == prior_profile_result

    def test_writes_back_fresh_result_under_the_current_revision(self, monkeypatch):
        """The write-back bug this test guards against: get_or_build_profile()
        never hands back which revision a *fresh* (cache-miss) profile is
        actually current as of, so profile_repo_with_cache() must resolve
        its own remote_head_sha() for the write-back rather than reusing
        (or worse, blanking) the prior value."""
        entry = _fake_product_entry()
        fresh_profile = RepositoryProfile(
            org_repo=entry.org_repo, detected_ecosystems=[], unresolved_manifests=["new.toml"]
        )
        backend = _FakeStateBackend()
        monkeypatch.setattr(orchestrator, "get_or_build_profile", lambda entry, **kw: fresh_profile)
        monkeypatch.setattr(orchestrator, "remote_head_sha", lambda clone_url: "current-sha")

        profile_repo_with_cache(entry, backend)

        stored = backend.load(entry.org_repo)
        assert stored.profile_cache.upstream_revision == "current-sha"
        assert stored.profile_cache.profile_result == fresh_profile.model_dump(mode="json")

    def test_backend_load_failure_still_returns_profile(self, monkeypatch):
        entry = _fake_product_entry()
        fresh_profile = RepositoryProfile(
            org_repo=entry.org_repo, detected_ecosystems=[], unresolved_manifests=[]
        )
        monkeypatch.setattr(orchestrator, "get_or_build_profile", lambda entry, **kw: fresh_profile)
        monkeypatch.setattr(orchestrator, "remote_head_sha", lambda clone_url: "sha")

        result = profile_repo_with_cache(entry, _RaisingStateBackend())

        assert result == fresh_profile

    def test_remote_head_sha_none_skips_write_back(self, monkeypatch):
        """No resolvable current revision means there's nothing correct to
        key a write-back by -- skip it rather than writing a wrong/blank
        one, mirroring get_or_build_profile()'s own probe-failure handling."""
        entry = _fake_product_entry()
        fresh_profile = RepositoryProfile(
            org_repo=entry.org_repo, detected_ecosystems=[], unresolved_manifests=[]
        )
        backend = _FakeStateBackend()
        monkeypatch.setattr(orchestrator, "get_or_build_profile", lambda entry, **kw: fresh_profile)
        monkeypatch.setattr(orchestrator, "remote_head_sha", lambda clone_url: None)

        result = profile_repo_with_cache(entry, backend)

        assert result == fresh_profile
        assert backend.load(entry.org_repo) is None


class TestRunRegistryProfilingSweep:
    """Decision #40, Part E: the actual registry-wide profiling loop --
    unlike run_registry(), sweeps every products.json entry regardless of
    mode (read-only, matching decision #40's require_listed() reasoning),
    with the same failure-isolation and disk-cleanup shape run_registry()
    already proved."""

    def test_sweeps_every_entry_regardless_of_mode(self, tmp_path, monkeypatch):
        (tmp_path / "data").mkdir()
        products = [
            {
                "family": "one",
                "platform": "java",
                "repo_name": "One",
                "repo_url": "https://github.com/acme/One",
                "clone_url": "https://github.com/acme/One.git",
                "active": True,
                "discovered_via": "manual",
                "mode": "full",
                "ecosystem": None,
                "policy_profile": None,
            },
            {
                "family": "two",
                "platform": "java",
                "repo_name": "Two",
                "repo_url": "https://github.com/acme/Two",
                "clone_url": "https://github.com/acme/Two.git",
                "active": True,
                "discovered_via": "manual",
                "mode": "disabled",
                "ecosystem": None,
                "policy_profile": None,
            },
        ]
        (tmp_path / "data" / "products.json").write_text(json.dumps(products), encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        seen = []

        def _fake_profile_repo_with_cache(entry, state_backend):
            seen.append(entry.org_repo)
            return RepositoryProfile(
                org_repo=entry.org_repo, detected_ecosystems=[], unresolved_manifests=[]
            )

        monkeypatch.setattr(orchestrator, "profile_repo_with_cache", _fake_profile_repo_with_cache)

        profiles = run_registry_profiling_sweep()

        assert sorted(seen) == ["acme/One", "acme/Two"]
        assert len(profiles) == 2

    def test_continues_past_one_entrys_failure(self, tmp_path, monkeypatch):
        (tmp_path / "data").mkdir()
        products = [
            {
                "family": "one",
                "platform": "java",
                "repo_name": "One",
                "repo_url": "https://github.com/acme/One",
                "clone_url": "https://github.com/acme/One.git",
                "active": True,
                "discovered_via": "manual",
                "mode": "full",
                "ecosystem": None,
                "policy_profile": None,
            },
            {
                "family": "two",
                "platform": "java",
                "repo_name": "Two",
                "repo_url": "https://github.com/acme/Two",
                "clone_url": "https://github.com/acme/Two.git",
                "active": True,
                "discovered_via": "manual",
                "mode": "full",
                "ecosystem": None,
                "policy_profile": None,
            },
        ]
        (tmp_path / "data" / "products.json").write_text(json.dumps(products), encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        def _flaky(entry, state_backend):
            if entry.repo_name == "One":
                raise RuntimeError("simulated profiling failure")
            return RepositoryProfile(
                org_repo=entry.org_repo, detected_ecosystems=[], unresolved_manifests=[]
            )

        monkeypatch.setattr(orchestrator, "profile_repo_with_cache", _flaky)

        profiles = run_registry_profiling_sweep()

        assert len(profiles) == 1
        assert profiles[0].org_repo == "acme/Two"

    def test_cleans_up_baseline_dir_after_each_entry(self, tmp_path, monkeypatch):
        (tmp_path / "data").mkdir()
        products = [
            {
                "family": "one",
                "platform": "java",
                "repo_name": "One",
                "repo_url": "https://github.com/acme/One",
                "clone_url": "https://github.com/acme/One.git",
                "active": True,
                "discovered_via": "manual",
                "mode": "full",
                "ecosystem": None,
                "policy_profile": None,
            }
        ]
        (tmp_path / "data" / "products.json").write_text(json.dumps(products), encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        def _fake_profile_repo_with_cache(entry, state_backend):
            baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
            baseline_path.mkdir(parents=True)
            (baseline_path / "stray.txt").write_text("x", encoding="utf-8")
            return RepositoryProfile(
                org_repo=entry.org_repo, detected_ecosystems=[], unresolved_manifests=[]
            )

        monkeypatch.setattr(orchestrator, "profile_repo_with_cache", _fake_profile_repo_with_cache)

        run_registry_profiling_sweep()

        assert not paths.baseline_dir("acme", "One").exists()


class TestStaleNoncompliantAndForceRegenerate:
    """Tier 1 SS1's compliance-vs-idempotency split: a policy tightened after
    generation must be detected (STALE_NONCOMPLIANT, zero LLM calls, block
    left untouched) and only overridden with an explicit --force-regenerate,
    never silently."""

    def test_tightening_word_limit_after_generation_yields_stale_noncompliant(
        self, tmp_path, monkeypatch
    ):
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        first = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)
        assert first.status == "GENERATED"
        rendered_text_before = first.work_readme_path.read_text(encoding="utf-8")

        # Tighten the policy below the word count of the prose we just rendered.
        policy_path = tmp_path / "config" / "policies" / "test-profile.yml"
        tightened = policy_path.read_text(encoding="utf-8").replace(
            "word_limit: { min: 10, max: 200 }", "word_limit: { min: 10, max: 5 }"
        )
        policy_path.write_text(tightened, encoding="utf-8")

        second = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)

        assert second.status == "STALE_NONCOMPLIANT"
        assert not second.llm_called
        assert second.work_readme_path.read_text(encoding="utf-8") == rendered_text_before

    def test_force_regenerate_overrides_the_stale_state(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)

        policy_path = tmp_path / "config" / "policies" / "test-profile.yml"
        tightened = policy_path.read_text(encoding="utf-8").replace(
            "word_limit: { min: 10, max: 200 }", "word_limit: { min: 10, max: 5 }"
        )
        policy_path.write_text(tightened, encoding="utf-8")

        forced = generate_repo(
            ORG_REPO,
            llm_mode="fixture",
            fixture_response_path=fixture_path,
            force_regenerate=True,
        )

        # Still calls the LLM (the only way to get new, shorter prose) and
        # still fails validation against the tightened limit, honestly --
        # force-regenerate re-tries, it doesn't fake compliance.
        assert forced.llm_called
        assert forced.status == "BLOCKED_VALIDATION_FAILED"

    def test_force_regenerate_preserves_previously_rendered_links(self, tmp_path, monkeypatch):
        """Real bug found live during the Phase 21 pilot re-proof
        (force-regenerating cells/java): org/com links that exist only
        inside the tool's own resources span -- not in raw baseline prose --
        must not be silently dropped just because force-regenerate only
        needed a fresh relationship paragraph. upsert_span replaces the
        whole span, so the render decision must re-detect every element
        against the span-stripped text, not trust gap_report computed from
        content that includes the very span about to be overwritten."""
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        first = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)
        assert first.status == "GENERATED"
        first_text = first.work_readme_path.read_text(encoding="utf-8")
        assert "products.example.org" in first_text
        assert "products.example.com" in first_text

        forced = generate_repo(
            ORG_REPO,
            llm_mode="fixture",
            fixture_response_path=fixture_path,
            force_regenerate=True,
        )

        assert forced.status == "GENERATED"
        forced_text = forced.work_readme_path.read_text(encoding="utf-8")
        assert "products.example.org" in forced_text
        assert "products.example.com" in forced_text

    def test_force_regenerate_of_a_stale_hash_render_does_not_spuriously_fail_idempotency(
        self, tmp_path, monkeypatch
    ):
        """Second real bug found in the same pilot re-proof: validation must
        check the hash actually embedded in the *freshly rendered* text, not
        the stale pre-render hash captured before this run started --
        otherwise a legitimate re-render (forced because the previously
        embedded hash was stale, e.g. after a GENERATION_SCHEMA_VERSION
        bump) always fails its own idempotency check, even though the fresh
        render is completely correct. Real cells/java evidence: the
        idempotency rule kept reporting the pre-bump hash as mismatched
        after a successful force-regenerate that had already fixed
        everything else."""
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        first = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)
        assert first.status == "GENERATED"

        # Simulate a stale embedded hash (e.g. left over from before a
        # GENERATION_SCHEMA_VERSION bump) by rewriting the work clone's
        # resources span with a hash that can never match a freshly-derived
        # one.
        work_readme_path = paths.work_dir("example-foss", "Example-FOSS-for-Java") / "README.md"
        stale_text = re.sub(
            r'hash="sha256:[0-9a-f]+"',
            'hash="sha256:' + "0" * 64 + '"',
            first.work_readme_path.read_text(encoding="utf-8"),
        )
        work_readme_path.write_text(stale_text, encoding="utf-8")

        forced = generate_repo(
            ORG_REPO,
            llm_mode="fixture",
            fixture_response_path=fixture_path,
            force_regenerate=True,
        )

        assert forced.status == "GENERATED"
        forced_text = forced.work_readme_path.read_text(encoding="utf-8")
        assert "products.example.org" in forced_text
        assert "products.example.com" in forced_text


class TestDurableStateFreshRunner:
    """Wave 4 / `RUN-001`'s concrete regression test: idempotency ("second
    run, zero LLM calls") must survive an ephemeral GitHub Actions runner
    being wiped between jobs, not just a reused local work clone (decision
    #12). Simulated as two *separate* runner working directories that share
    only the durable state backend and the same upstream source -- the
    second one's local work clone is genuinely fresh, never cloned before,
    exactly the fresh-runner scenario `paths.work_dir()`'s persistence
    cannot cover by itself."""

    def test_fresh_runner_with_no_local_marker_skips_using_durable_state_alone(
        self, tmp_path, monkeypatch
    ):
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        backend = _FakeStateBackend()

        runner_one = tmp_path / "runner-one"
        runner_one.mkdir()
        fixture_path_one = _setup_project_root(runner_one, str(source), mode="full")
        monkeypatch.chdir(runner_one)
        first = generate_repo(
            ORG_REPO,
            llm_mode="fixture",
            fixture_response_path=fixture_path_one,
            state_backend=backend,
        )
        assert first.status == "GENERATED"
        assert first.llm_called

        runner_two = tmp_path / "runner-two"
        runner_two.mkdir()
        fixture_path_two = _setup_project_root(runner_two, str(source), mode="full")
        monkeypatch.chdir(runner_two)

        second = generate_repo(
            ORG_REPO,
            llm_mode="fixture",
            fixture_response_path=fixture_path_two,
            state_backend=backend,
        )

        assert second.status == first.status
        assert not second.llm_called
        assert second.llm_calls == []

    def test_without_a_state_backend_behavior_is_unchanged(self, tmp_path, monkeypatch):
        """No `state_backend` passed (every existing caller, today) must
        behave exactly as before Wave 4 -- a second fresh runner with no
        shared backend still calls the LLM, since nothing durable exists."""
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)

        runner_one = tmp_path / "runner-one"
        runner_one.mkdir()
        fixture_path_one = _setup_project_root(runner_one, str(source), mode="full")
        monkeypatch.chdir(runner_one)
        first = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path_one)
        assert first.llm_called

        runner_two = tmp_path / "runner-two"
        runner_two.mkdir()
        fixture_path_two = _setup_project_root(runner_two, str(source), mode="full")
        monkeypatch.chdir(runner_two)
        second = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path_two)

        assert second.llm_called  # no durable backend -- nothing to remember the prior run by

    def test_unreachable_state_backend_does_not_abort_the_run(self, tmp_path, monkeypatch):
        """`RUN-003` regression: found live via an `act` reproduction of
        `readme-agent-run.yml` where `actions/checkout` didn't persist push
        credentials, making the real `git push` fail with
        `StateBackendError` -- uncaught, it aborted the whole run and lost
        the evidence bundle for work that had already succeeded. A backend
        that raises on every call must degrade to "not remembered," not
        take the run down (mirrors `inspect_repo`'s `check_install`
        convention)."""
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        result = generate_repo(
            ORG_REPO,
            llm_mode="fixture",
            fixture_response_path=fixture_path,
            state_backend=_RaisingStateBackend(),
        )

        assert result.status == "GENERATED"
        assert result.llm_called
        assert result.evidence_dir is not None
        assert (result.evidence_dir / "manifest.json").exists()

    def test_fresh_runner_with_changed_upstream_content_does_not_blindly_skip(
        self, tmp_path, monkeypatch
    ):
        """Decision #38's concrete regression test. Before the fix,
        `durable_skip` required only `accepted_facts_hash == facts_hash` --
        and `facts_hash` deliberately excludes README content (decision #11),
        so a real upstream README edit between two fresh-runner calls was
        silently invisible: the second call would blindly copy
        `durable_state.accepted_status` without ever looking at the (changed)
        content. Same two-separate-runner-directories shape as
        `test_fresh_runner_with_no_local_marker_skips_using_durable_state_alone`
        above, but the upstream `source` repo's README is genuinely edited in
        between -- proving the second call now re-examines real content
        instead of trusting stale history."""
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        backend = _FakeStateBackend()

        runner_one = tmp_path / "runner-one"
        runner_one.mkdir()
        fixture_path_one = _setup_project_root(runner_one, str(source), mode="full")
        monkeypatch.chdir(runner_one)
        first = generate_repo(
            ORG_REPO,
            llm_mode="fixture",
            fixture_response_path=fixture_path_one,
            state_backend=backend,
        )
        assert first.status == "GENERATED"
        assert first.llm_called

        # A real upstream edit -- prose only, so manifest/license/policy (and
        # therefore facts_hash) stay identical to the first call. Isolates
        # the content-fingerprint gate from facts_hash's own, separate check.
        edited_readme = (
            BLANK_SLATE_README
            + "\nThis edit simulates a real maintainer updating the README upstream.\n"
        )
        (source / "README.md").write_text(edited_readme, encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "docs: update description"], cwd=source)

        runner_two = tmp_path / "runner-two"
        runner_two.mkdir()
        fixture_path_two = _setup_project_root(runner_two, str(source), mode="full")
        monkeypatch.chdir(runner_two)

        second = generate_repo(
            ORG_REPO,
            llm_mode="fixture",
            fixture_response_path=fixture_path_two,
            state_backend=backend,
        )

        assert second.facts_hash == first.facts_hash  # confirms this isolates the fingerprint gate
        assert second.llm_called  # must re-examine and re-render, not blindly trust history
        rendered = second.work_readme_path.read_text(encoding="utf-8")
        assert "This edit simulates a real maintainer updating the README upstream." in rendered
        assert second.status == "GENERATED"

    def test_record_accepted_state_preserves_domain_states_and_supervisor_state(
        self, tmp_path, monkeypatch
    ):
        """Decision #38's second bug fix, verified directly: before this fix,
        `_record_accepted_state()` built a brand-new `RunStateV1(...)` from
        scratch on every write, silently dropping `domain_states`/
        `supervisor_state` -- live today for `supervisor_state`, since
        `supervisor/loop.py::supervise_repo()` already writes it. Seeds the
        backend with both fields pre-populated (as if `supervise` already ran
        for this repo), then runs a normal `generate_repo(state_backend=...)`
        call and confirms both survive."""
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        backend = _FakeStateBackend()
        backend.save(
            ORG_REPO,
            RunStateV1(
                org_repo=ORG_REPO,
                domain_states={
                    "readme_reconciliation": DomainStateV1(
                        domain="readme_reconciliation", accepted_status="NO_CHANGE"
                    )
                },
                supervisor_state=SupervisorStateV1(last_status="CONVERGED_NO_CHANGE"),
            ),
            expected_version=None,
        )

        result = generate_repo(
            ORG_REPO,
            llm_mode="fixture",
            fixture_response_path=fixture_path,
            state_backend=backend,
        )
        assert result.status == "GENERATED"

        after = backend.load(ORG_REPO)
        assert after is not None
        assert after.domain_states["readme_reconciliation"].accepted_status == "NO_CHANGE"
        assert after.supervisor_state is not None
        assert after.supervisor_state.last_status == "CONVERGED_NO_CHANGE"
        # And the fields this call actually owns were updated, not ignored.
        assert after.accepted_facts_hash == result.facts_hash
        assert after.accepted_status == "GENERATED"


def _init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-b", "main"], cwd=path)
    run_git(["config", "user.email", "test@example.com"], cwd=path)
    run_git(["config", "user.name", "Test"], cwd=path)
    (path / "README.md").write_text("# test\n", encoding="utf-8")
    run_git(["add", "."], cwd=path)
    run_git(["commit", "-m", "initial"], cwd=path)
    return path


class TestEnsureWorkCloneValidity:
    """Found live, 2026-07-22: `_ensure_work_clone()`'s reuse check only
    verified `.git` exists as a directory, never that it's a genuinely valid,
    complete repository. A work clone left incomplete (interrupted mid-clone,
    or corrupted) still passed that check, was "reused," and then had
    `neuter_push()` called against it -- which silently walked up to and
    disabled push on the *parent* directory's repo instead, since git treats
    an incomplete `.git` the same as "not a repo here, check the parent."
    These tests prove the fix: an invalid `.git` is never reused, and a
    valid one still is (no regression to the decision #38 fast path)."""

    def test_valid_clone_is_reused(self, tmp_path):
        from readme_agent.readme.candidate_workspace import ensure_work_clone

        baseline = _init_git_repo(tmp_path / "baseline")
        work_path = tmp_path / "work"
        entry = SimpleNamespace(
            org_repo="acme/widget", repo_url="https://example.invalid/acme/widget"
        )

        first = ensure_work_clone(entry, baseline, work_path, fresh_fingerprint="fp-1")
        second = ensure_work_clone(entry, baseline, work_path, fresh_fingerprint="fp-1")

        assert first == work_path
        assert second == work_path
        # Proves reuse actually happened, not a silent re-clone: the git
        # identity create_work_clone() sets is still there from the first call.
        assert run_git(["config", "user.name"], cwd=work_path).stdout.strip() == "readme-agent"

    def test_incomplete_git_dir_is_not_reused(self, tmp_path):
        """The exact shape found live: only `hooks/`+`objects/`, missing
        `HEAD`/`config`/`index`/`refs` -- git silently resolves operations
        against the nearest valid PARENT repo instead of failing."""
        baseline = _init_git_repo(tmp_path / "baseline")
        work_path = tmp_path / "work"
        (work_path / ".git" / "hooks").mkdir(parents=True)
        (work_path / ".git" / "objects").mkdir(parents=True)
        from readme_agent.readme.candidate_workspace import (
            ensure_work_clone,
            work_clone_fingerprint_sidecar,
        )

        sidecar = work_clone_fingerprint_sidecar(work_path)
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text("fp-1", encoding="utf-8")
        entry = SimpleNamespace(
            org_repo="acme/widget", repo_url="https://example.invalid/acme/widget"
        )

        result = ensure_work_clone(entry, baseline, work_path, fresh_fingerprint="fp-1")

        # A real, complete clone was built instead of trusting the broken one.
        assert result == work_path
        assert (work_path / ".git" / "HEAD").exists()
        assert (work_path / ".git" / "config").exists()

    def test_is_valid_work_clone_rejects_a_walk_up_to_parent(self, tmp_path):
        """Direct proof of the exact bug: a `.git` missing HEAD/config/refs
        makes `rev-parse --show-toplevel` resolve to an ANCESTOR directory,
        not `work_path` itself -- `_is_valid_work_clone` must catch this even
        though git itself doesn't report an error."""
        _init_git_repo(tmp_path)  # tmp_path itself is a valid repo (the "parent")
        work_path = tmp_path / "work"
        (work_path / ".git" / "hooks").mkdir(parents=True)
        (work_path / ".git" / "objects").mkdir(parents=True)

        from readme_agent.readme.candidate_workspace import is_valid_work_clone

        assert is_valid_work_clone(work_path) is False

    def test_is_valid_work_clone_accepts_a_real_clone(self, tmp_path):
        from readme_agent.readme.candidate_workspace import (
            ensure_work_clone,
            is_valid_work_clone,
        )

        baseline = _init_git_repo(tmp_path / "baseline")
        work_path = tmp_path / "work"
        entry = SimpleNamespace(
            org_repo="acme/widget", repo_url="https://example.invalid/acme/widget"
        )
        ensure_work_clone(entry, baseline, work_path, fresh_fingerprint="fp-1")

        assert is_valid_work_clone(work_path) is True
