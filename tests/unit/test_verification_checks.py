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
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.gitsafety._git import run_git
from readme_agent.orchestrator import prepare_readme_candidate
from readme_agent.verification import checks as verification_checks
from readme_agent.verification.checks import (
    _verify_presentation_candidate,
    compute_verification_token,
    independently_verify_readme_candidate,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ORG_REPO = "example-foss/Aspose.Thing-FOSS-for-Java"

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
            "repo_name": "Aspose.Thing-FOSS-for-Java",
            "repo_url": "https://github.com/example-foss/Aspose.Thing-FOSS-for-Java",
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


class TestComputeVerificationToken:
    """TC-28 (decision #46's own deferred scope from TC-15): the nonce
    argument is what makes a token minted for a given org_repo/facts_hash/
    fresh_fingerprint in one run rejectable if replayed into a later, separate
    run -- these tests exercise the function directly, independent of the
    commit_readme_write.precheck() integration tests in test_capabilities.py."""

    def test_identical_inputs_produce_the_same_token(self):
        args = ("acme/widget", "hash1", "fp1", "nonce1")
        assert compute_verification_token(*args) == compute_verification_token(*args)

    def test_a_different_nonce_alone_changes_the_token(self):
        token_a = compute_verification_token("acme/widget", "hash1", "fp1", "nonce-a")
        token_b = compute_verification_token("acme/widget", "hash1", "fp1", "nonce-b")
        assert token_a != token_b

    def test_a_different_facts_hash_alone_changes_the_token(self):
        token_a = compute_verification_token("acme/widget", "hash1", "fp1", "nonce1")
        token_b = compute_verification_token("acme/widget", "hash2", "fp1", "nonce1")
        assert token_a != token_b


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
        work_path = paths.work_dir("example-foss", "Aspose.Thing-FOSS-for-Java")
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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPLETE_FACTS_PROOF = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)


def _complete_snapshot_facts() -> ProductFactsV2:
    proof = json.loads(COMPLETE_FACTS_PROOF.read_text(encoding="utf-8"))
    pilot = next(
        item
        for item in proof["current_pilots"]
        if item["org_repo"] == "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    )
    return ProductFactsV2.model_validate(pilot["product_facts_v2"])


class TestVerifyPresentationCandidateDispositionWiring:
    """Two-gate finding, extended (2026-08-19): this independent verifier
    (gate 3) re-derives the document plan the same way gate 2 (readme_
    factuality.py) does and had the identical gap -- no disposition context
    passed through to build_readme_document_candidate(), so an accepted
    `excluded_with_reason` claim (gate 1) could reappear as a fresh block
    here too (live-observed on barcode-python after the gate-2 fix landed).
    Proves the wiring directly on the private helper rather than through
    independently_verify_readme_candidate()'s full fixture, which never
    exercises the presentation-candidate branch."""

    class _StopAfterCapture(Exception):
        """Short-circuits before the rest of the function needs a real,
        self-consistent facts/source/candidate triple -- only the exact
        kwargs build_readme_document_candidate() receives are under test
        here, not the full independent-rebuild-and-compare behavior (already
        covered by the other tests in this file and by the module's own
        composition-lineage/document-plan test suites)."""

    def _mock_facts_and_spy(self, monkeypatch):
        facts = _complete_snapshot_facts()
        monkeypatch.setattr(
            verification_checks,
            "collect_product_facts",
            lambda org_repo: {"product_facts_v2": facts.model_dump(mode="json")},
        )
        captured: dict = {}

        def spy_build(*_args, **kwargs):
            captured["llm_disposition_client"] = kwargs.get("llm_disposition_client")
            captured["repository_root"] = kwargs.get("repository_root")
            captured["disposition_ratchet_path"] = kwargs.get("disposition_ratchet_path")
            raise self._StopAfterCapture

        monkeypatch.setattr(verification_checks, "build_readme_document_candidate", spy_build)
        return facts, captured

    def test_disposition_context_reaches_the_independent_rebuild(self, monkeypatch):
        facts, captured = self._mock_facts_and_spy(monkeypatch)

        sentinel_client = object()
        sentinel_root = Path("/sentinel/repository/root")
        sentinel_ratchet = Path("/sentinel/ratchet.json")
        try:
            _verify_presentation_candidate(
                facts.org_repo,
                "# Anything\n",
                llm_disposition_client=sentinel_client,
                repository_root=sentinel_root,
                disposition_ratchet_path=sentinel_ratchet,
            )
        except self._StopAfterCapture:
            pass

        assert captured["llm_disposition_client"] is sentinel_client
        assert captured["repository_root"] == sentinel_root
        assert captured["disposition_ratchet_path"] == sentinel_ratchet

    def test_disposition_context_defaults_to_none(self, monkeypatch):
        facts, captured = self._mock_facts_and_spy(monkeypatch)

        try:
            _verify_presentation_candidate(facts.org_repo, "# Anything\n")
        except self._StopAfterCapture:
            pass

        assert captured["llm_disposition_client"] is None
        assert captured["repository_root"] is None
        assert captured["disposition_ratchet_path"] is None
