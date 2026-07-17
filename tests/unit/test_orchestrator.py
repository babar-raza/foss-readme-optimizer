"""End-to-end control-flow proof against synthetic local git repos -- no
network, no real secrets. Mirrors the three real pilot states found in the
2026-07-17 README audit: blank-slate (cells/java), fully-compliant (3d/java),
partial-gap (pdf/java).
"""

import json

import pytest

from readme_agent.errors import NotAllowlistedError
from readme_agent.gitsafety._git import run_git
from readme_agent.orchestrator import generate_repo, run_repo

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
            "ecosystem": "maven",
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


class TestBlankSlateRepo:
    """Mirrors cells/java: nothing present, needs a real LLM call."""

    def test_first_run_generates_and_calls_the_llm(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# Example FOSS for Java\n\nIntro.\n")
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        result = generate_repo(ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path)

        assert result.status == "GENERATED"
        assert result.llm_called
        text = result.work_readme_path.read_text(encoding="utf-8")
        assert "products.example.org" in text
        assert "products.example.com" in text
        assert "free, open-source FOSS edition" in text

    def test_second_run_is_idempotent_zero_llm_calls(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# Example FOSS for Java\n\nIntro.\n")
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
        assert result.gap_report.fully_compliant
        # Never touched: file on disk still equals what was originally cloned.
        assert result.work_readme_path.read_text(encoding="utf-8") == compliant_readme


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


class TestRunModeFullCommitsLocally:
    def test_full_mode_commits_locally_never_pushes(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# Example FOSS for Java\n\nIntro.\n")
        fixture_path = _setup_project_root(tmp_path, str(source), mode="full")
        monkeypatch.chdir(tmp_path)

        result = run_repo(
            ORG_REPO, mode="full", llm_mode="fixture", fixture_response_path=fixture_path
        )

        assert result.ok
        assert result.status == "GENERATED"
        assert result.committed
        assert result.push_block_ok


class TestStaleNoncompliantAndForceRegenerate:
    """Tier 1 SS1's compliance-vs-idempotency split: a policy tightened after
    generation must be detected (STALE_NONCOMPLIANT, zero LLM calls, block
    left untouched) and only overridden with an explicit --force-regenerate,
    never silently."""

    def test_tightening_word_limit_after_generation_yields_stale_noncompliant(
        self, tmp_path, monkeypatch
    ):
        source = _init_source_repo(tmp_path / "source", "# Example FOSS for Java\n\nIntro.\n")
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
        source = _init_source_repo(tmp_path / "source", "# Example FOSS for Java\n\nIntro.\n")
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
