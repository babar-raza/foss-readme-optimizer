"""Wave 8: `verification/checks.py::independently_verify_readme_candidate()`
-- re-derives ground truth from a fresh on-disk read and the repo's own
policy, rather than trusting a caller's claimed status/needs_write/
final_text. Reuses `test_orchestrator.py`'s own proven fixture policy/README/
LLM-response combination so the "accept" path exercises a genuinely valid,
real GENERATED candidate, not a hand-crafted one that might accidentally
satisfy the verifier's checks without actually satisfying the real
validation rules."""

import json
from pathlib import Path

from readme_agent import paths
from readme_agent.gitsafety._git import run_git
from readme_agent.orchestrator import prepare_readme_candidate
from readme_agent.verification.checks import independently_verify_readme_candidate

REPO_ROOT = Path(__file__).resolve().parents[2]
ORG_REPO = "example-foss/Example-FOSS-for-Java"

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


def _setup_project_root(tmp_path, source_clone_url: str):
    (tmp_path / "data").mkdir()
    (tmp_path / "config" / "policies").mkdir(parents=True)
    # Wave 8.5: llm.prompts.prompt_content_hash() reads
    # prompts/generation/relationship_explained.yaml fresh, cwd-relative, on
    # every call -- staged here so it doesn't raise after monkeypatch.chdir().
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
            "mode": "full",
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


class TestIndependentlyVerifyReadmeCandidate:
    def test_a_genuinely_valid_generated_candidate_is_accepted(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        fixture_path = _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)

        candidate = prepare_readme_candidate(
            ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path
        )
        assert candidate.status == "GENERATED"  # sanity: a real, valid render

        verdict = independently_verify_readme_candidate(
            ORG_REPO, candidate.final_text, candidate.status, needs_write=True
        )

        assert verdict["verdict"] == "accept"
        assert verdict["requirement_map"] == {
            "license_mentioned": True,
            "products_org_link": True,
            "products_com_link": True,
            "relationship_explained": True,
        }

    def test_claimed_needs_write_mismatching_the_actual_comparison_is_rejected(
        self, tmp_path, monkeypatch
    ):
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        fixture_path = _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        candidate = prepare_readme_candidate(
            ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path
        )

        # candidate.final_text genuinely differs from the current on-disk
        # README (nothing has been written yet) -- claiming needs_write=False
        # is a lie an independent re-derivation must catch.
        verdict = independently_verify_readme_candidate(
            ORG_REPO, candidate.final_text, candidate.status, needs_write=False
        )

        assert verdict["verdict"] == "reject"
        assert verdict["checks"]["needs_write_matches"] is False

    def test_the_known_defect_regression_a_falsely_generated_candidate_is_rejected(
        self, tmp_path, monkeypatch
    ):
        """The concrete fix for the already-known defect: `specialists/
        readme_presentation.py::_commit_node()` previously durably accepted a
        BLOCKED_VALIDATION_FAILED candidate's facts_hash unconditionally --
        this proves the verifier independently catches exactly that case,
        even when the caller falsely claims status=GENERATED."""
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        fixture_path = _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        candidate = prepare_readme_candidate(
            ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path
        )
        assert candidate.status == "GENERATED"

        # A real hard-validation-failure shape (a prohibited term) injected
        # into an otherwise-valid, already-rendered candidate, while the
        # caller (mimicking the found defect) still falsely claims
        # status="GENERATED".
        broken_text = candidate.final_text.replace(
            "Java library", "Java library that we guarantee works"
        )

        verdict = independently_verify_readme_candidate(
            ORG_REPO, broken_text, "GENERATED", needs_write=True
        )

        assert verdict["verdict"] == "reject"
        assert verdict["checks"]["validation_passed"] is False

    def test_needs_write_false_with_a_non_compliant_status_is_rejected(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        # prepare_readme_candidate never writes -- the on-disk README stays
        # exactly BLANK_SLATE_README, so claiming needs_write=False with
        # final_text == BLANK_SLATE_README matches reality.
        work_path = paths.work_dir("example-foss", "Example-FOSS-for-Java")
        work_path.mkdir(parents=True, exist_ok=True)
        (work_path / "README.md").write_text(BLANK_SLATE_README, encoding="utf-8")

        verdict = independently_verify_readme_candidate(
            ORG_REPO, BLANK_SLATE_README, "STALE_NONCOMPLIANT", needs_write=False
        )

        assert verdict["verdict"] == "reject"

    def test_needs_write_true_with_a_non_generated_status_is_rejected(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", BLANK_SLATE_README)
        fixture_path = _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        candidate = prepare_readme_candidate(
            ORG_REPO, llm_mode="fixture", fixture_response_path=fixture_path
        )

        verdict = independently_verify_readme_candidate(
            ORG_REPO, candidate.final_text, "BLOCKED_VALIDATION_FAILED", needs_write=True
        )

        assert verdict["verdict"] == "reject"
