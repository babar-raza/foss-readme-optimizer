"""Two-layer secret-scan safety net.

Layer 1 (deterministic, always runs in CI, no real secrets needed): a
synthetic fake-secret-shaped env var must come out masked.

Layer 2 (opportunistic, meaningful locally where real keys are set, a
harmless no-op in CI where they aren't): after a full fixture-mode
`generate` run, grep the entire evidence tree for the literal live secret
values -- this is this project's own norm (see .env.example / plan) applied
to itself, not a hypothetical.
"""

import json
import os
from pathlib import Path

from readme_agent import env
from readme_agent.evidence.redaction import redact
from readme_agent.gitsafety._git import run_git
from readme_agent.orchestrator import generate_repo

REPO_ROOT = Path(__file__).resolve().parents[2]

POM_XML = "<project><groupId>x</groupId><artifactId>y</artifactId><version>1</version></project>"
FIXTURE_RESPONSE = {
    "relationship_paragraph": (
        "This repository is the free, open-source FOSS edition of the "
        "corresponding commercial product. Upgrade to the commercial "
        "edition for a broader feature set and dedicated support."
    ),
    "talking_points_covered": ["open_source_scope", "commercial_upgrade_path"],
    "claims": {"license_name": "MIT", "commercial_link_url": "https://products.example.com/x/"},
}
POLICY_YAML = """schema_version: 2
policy_profile: sec-test-profile
required_elements:
  license_mentioned:
    detected_license: MIT
  products_org_link:
    url: "https://products.example.org/x/"
    family_url: "https://products.example.org/"
    label: "X"
  products_com_link:
    url: "https://products.example.com/x/"
    family_url: "https://products.example.com/"
    label: "X"
  relationship_explained:
    min_sentences: 2
    talking_points: [open_source_scope, commercial_upgrade_path]
secondary_links: []
block:
  word_limit: { min: 5, max: 200 }
  prohibited_terms: []
  link_whitelist_domains: [products.example.com, products.example.org]
"""


class TestDeterministicLayer:
    def test_synthetic_secret_shaped_value_is_masked_without_real_secrets(self, monkeypatch):
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GPT_OSS_API_KEY", raising=False)

        fake_secret = "ghp_thisIsASyntheticFakeTokenForTesting1234"
        text = f"Authorization used token {fake_secret}"

        redacted = redact(text)

        assert fake_secret not in redacted
        assert "[REDACTED]" in redacted


class TestOpportunisticLayer:
    def test_no_live_secret_value_ever_reaches_the_evidence_tree(self, tmp_path, monkeypatch):
        live_secrets = env.secret_values()
        if not live_secrets:
            return  # harmless no-op when no real secrets are set, e.g. in CI

        source = tmp_path / "source"
        source.mkdir()
        run_git(["init", "-b", "main"], cwd=source)
        run_git(["config", "user.email", "t@example.com"], cwd=source)
        run_git(["config", "user.name", "T"], cwd=source)
        (source / "README.md").write_text("# X\n\nIntro.\n", encoding="utf-8")
        (source / "pom.xml").write_text(POM_XML, encoding="utf-8")
        (source / "LICENSE").write_text("MIT License", encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "initial"], cwd=source)

        (tmp_path / "data").mkdir()
        (tmp_path / "config" / "policies").mkdir(parents=True)
        prompt_dir = tmp_path / "prompts" / "relationship_explained"
        prompt_dir.mkdir(parents=True)
        for asset in ("system.txt", "user.txt"):
            (prompt_dir / asset).write_text(
                (REPO_ROOT / "prompts" / "relationship_explained" / asset).read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
        products = [
            {
                "family": "x",
                "platform": "java",
                "repo_name": "X-FOSS-for-Java",
                "repo_url": "https://github.com/x-foss/X-FOSS-for-Java",
                "clone_url": str(source),
                "active": True,
                "discovered_via": "manual",
                "mode": "full",
                "ecosystem": "java",
                "policy_profile": "sec-test-profile",
            }
        ]
        (tmp_path / "data" / "products.json").write_text(json.dumps(products), encoding="utf-8")
        (tmp_path / "config" / "policies" / "sec-test-profile.yml").write_text(
            POLICY_YAML, encoding="utf-8"
        )
        fixture_path = tmp_path / "fixture_response.json"
        fixture_path.write_text(json.dumps(FIXTURE_RESPONSE), encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        result = generate_repo(
            "x-foss/X-FOSS-for-Java", llm_mode="fixture", fixture_response_path=fixture_path
        )
        assert result.evidence_dir is not None

        for root, _dirs, files in os.walk(result.evidence_dir):
            for filename in files:
                path_obj = os.path.join(root, filename)
                content = open(path_obj, encoding="utf-8", errors="replace").read()
                for secret in live_secrets:
                    assert secret not in content, f"live secret leaked into {path_obj}"
