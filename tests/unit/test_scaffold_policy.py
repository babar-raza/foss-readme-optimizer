"""ONB-004: `readme-agent scaffold-policy` -- pre-fills a policy profile YAML
using live-verified facts, never a guessed URL/license. Network calls are
monkeypatched at the `registry.policy_facts.verify_repo_facts` seam so this
stays offline, matching this project's own `@pytest.mark.live` convention.
"""

import argparse
import json

import pytest
import yaml

from readme_agent.commands import cmd_scaffold_policy

_ENTRY = {
    "family": "words",
    "platform": "net",
    "repo_name": "Aspose.Words-FOSS-for-.NET",
    "repo_url": "https://github.com/aspose-words-foss/Aspose.Words-FOSS-for-.NET",
    "clone_url": "https://github.com/aspose-words-foss/Aspose.Words-FOSS-for-.NET.git",
    "active": True,
    "discovered_via": "github",
    "mode": "disabled",
    "ecosystem": None,
    "policy_profile": None,
}
_ORG_REPO = "aspose-words-foss/Aspose.Words-FOSS-for-.NET"


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "products.json").write_text(
        json.dumps([_ENTRY], indent=2), encoding="utf-8"
    )
    (tmp_path / "config" / "policies").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _fully_verified_facts(**overrides):
    facts = {
        "org_repo": _ORG_REPO,
        "family": "words",
        "platform": "net",
        "license": "MIT",
        "org_family_url": "https://products.aspose.org/words/",
        "org_family_status": 200,
        "org_platform_url": "https://products.aspose.org/words/net/",
        "org_platform_status": 404,
        "com_family_url": "https://products.aspose.com/words/",
        "com_family_status": 200,
        "com_platform_url": "https://products.aspose.com/words/net/",
        "com_platform_status": 200,
    }
    facts.update(overrides)
    return facts


def test_writes_verified_profile_with_family_fallback_for_org_link(project, monkeypatch):
    from readme_agent.registry import policy_facts as policy_facts_module

    monkeypatch.setattr(
        policy_facts_module, "verify_repo_facts", lambda *a, **k: _fully_verified_facts()
    )

    args = argparse.Namespace(repo=_ORG_REPO, force=False)
    exit_code = cmd_scaffold_policy(args)

    assert exit_code == 0
    out = project / "config" / "policies" / "aspose-words-foss-net.yml"
    assert out.exists()
    profile = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert profile["policy_profile"] == "aspose-words-foss-net"
    assert profile["required_elements"]["license_mentioned"]["detected_license"] == "MIT"
    # org platform 404'd -- must fall back to the family-level link, never a
    # guessed platform URL that wasn't actually confirmed.
    assert (
        profile["required_elements"]["products_org_link"]["url"]
        == "https://products.aspose.org/words/"
    )
    assert (
        profile["required_elements"]["products_com_link"]["url"]
        == "https://products.aspose.com/words/net/"
    )
    assert profile["required_elements"]["products_com_link"]["label"] == "Aspose.Words for .NET"

    from readme_agent.registry.loader import load_policy

    # Full round-trip through the real pydantic schema, not just YAML parsing.
    loaded = load_policy("aspose-words-foss-net", project / "config" / "policies")
    assert loaded.policy_profile == "aspose-words-foss-net"


def test_unverifiable_facts_become_explicit_todos_not_guesses(project, monkeypatch):
    from readme_agent.registry import policy_facts as policy_facts_module

    monkeypatch.setattr(
        policy_facts_module,
        "verify_repo_facts",
        lambda *a, **k: _fully_verified_facts(
            license=None, org_family_status=404, com_family_status=404, com_platform_status=404
        ),
    )

    args = argparse.Namespace(repo=_ORG_REPO, force=False)
    cmd_scaffold_policy(args)

    out = project / "config" / "policies" / "aspose-words-foss-net.yml"
    profile = yaml.safe_load(out.read_text(encoding="utf-8"))
    required = profile["required_elements"]
    assert required["license_mentioned"]["detected_license"].startswith("TODO(human)")
    assert required["products_org_link"]["url"].startswith("TODO(human)")
    assert required["products_com_link"]["url"].startswith("TODO(human)")


def test_refuses_to_overwrite_without_force(project, monkeypatch):
    from readme_agent.registry import policy_facts as policy_facts_module

    monkeypatch.setattr(
        policy_facts_module, "verify_repo_facts", lambda *a, **k: _fully_verified_facts()
    )
    args = argparse.Namespace(repo=_ORG_REPO, force=False)
    assert cmd_scaffold_policy(args) == 0

    # Second call, no --force: must refuse rather than clobber a possibly
    # human-edited file.
    assert cmd_scaffold_policy(args) == 2


def test_force_overwrites_an_existing_profile(project, monkeypatch):
    from readme_agent.registry import policy_facts as policy_facts_module

    monkeypatch.setattr(
        policy_facts_module, "verify_repo_facts", lambda *a, **k: _fully_verified_facts()
    )
    args = argparse.Namespace(repo=_ORG_REPO, force=False)
    cmd_scaffold_policy(args)

    args_force = argparse.Namespace(repo=_ORG_REPO, force=True)
    assert cmd_scaffold_policy(args_force) == 0


def test_unknown_repo_exits_2(project):
    args = argparse.Namespace(repo="not-listed/nope", force=False)
    assert cmd_scaffold_policy(args) == 2


def test_does_not_touch_products_json(project, monkeypatch):
    """Wiring ecosystem/policy_profile into the registry stays a separate,
    deliberate human step -- this command only writes the YAML."""
    from readme_agent.registry import policy_facts as policy_facts_module

    monkeypatch.setattr(
        policy_facts_module, "verify_repo_facts", lambda *a, **k: _fully_verified_facts()
    )
    before = (project / "data" / "products.json").read_text(encoding="utf-8")

    args = argparse.Namespace(repo=_ORG_REPO, force=False)
    cmd_scaffold_policy(args)

    after = (project / "data" / "products.json").read_text(encoding="utf-8")
    assert before == after
