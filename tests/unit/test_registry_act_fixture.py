"""ACT-only registry inventory fixture controls."""

from pathlib import Path

import pytest

from readme_agent.errors import UsageError
from readme_agent.registry.act_fixture import build_act_registry_inventory
from readme_agent.registry.loader import load_products


def test_fixture_is_rejected_outside_act(monkeypatch):
    monkeypatch.delenv("ACT", raising=False)
    monkeypatch.setenv("README_AGENT_PRODUCTION_AUTH", "act_local")

    with pytest.raises(UsageError, match="only under ACT=true"):
        build_act_registry_inventory(Path("data/products.json"))


def test_fixture_is_rejected_for_non_act_authentication(monkeypatch):
    monkeypatch.setenv("ACT", "true")
    monkeypatch.setenv("README_AGENT_PRODUCTION_AUTH", "github_app")

    with pytest.raises(UsageError, match="requires the act_local"):
        build_act_registry_inventory(Path("data/products.json"))


def test_fixture_covers_the_dynamic_registry_and_every_configured_source(monkeypatch):
    monkeypatch.setenv("ACT", "true")
    monkeypatch.setenv("README_AGENT_PRODUCTION_AUTH", "act_local")

    inventory = build_act_registry_inventory(Path("data/products.json"))
    entries = load_products()

    assert inventory.complete is True
    assert len(inventory.observations) == len(entries)
    assert {item.full_name for item in inventory.observations} == {
        entry.org_repo for entry in entries
    }
    assert {source.status for source in inventory.sources} == {"complete", "excluded"}
    assert [source.source.organization for source in inventory.exclusions] == [
        "aspose-imaging-foss"
    ]
    assert sum(source.observation_count for source in inventory.sources) == len(entries)


def test_fixture_retains_an_injected_source_outage(monkeypatch):
    monkeypatch.setenv("ACT", "true")
    monkeypatch.setenv("README_AGENT_PRODUCTION_AUTH", "act_local")
    monkeypatch.setenv("README_AGENT_ACT_REGISTRY_SOURCE_FAILURE", "aspose-note-foss")

    inventory = build_act_registry_inventory(Path("data/products.json"))
    failure = next(
        source for source in inventory.sources if source.source.organization == "aspose-note-foss"
    )

    assert inventory.complete is False
    assert failure.status == "failed"
    assert failure.error == "injected ACT source outage"


def test_fixture_rejects_outage_injection_for_excluded_source(monkeypatch):
    monkeypatch.setenv("ACT", "true")
    monkeypatch.setenv("README_AGENT_PRODUCTION_AUTH", "act_local")
    monkeypatch.setenv("README_AGENT_ACT_REGISTRY_SOURCE_FAILURE", "aspose-imaging-foss")

    with pytest.raises(UsageError, match="cannot inject an outage for excluded source"):
        build_act_registry_inventory(Path("data/products.json"))
