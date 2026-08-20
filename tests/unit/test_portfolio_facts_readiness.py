"""Facts-only portfolio readiness driver: loops the real registry, recomputes
freshness live (stubbed offline here), and never fabricates a readiness
verdict for a repository whose facts were not supplied."""

from __future__ import annotations

from readme_agent.facts.portfolio_facts_readiness import (
    RepositoryFreshnessV1,
    portfolio_facts_readiness,
    processable_registry_entries,
)
from readme_agent.facts.resolution import resolve_product_facts
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2


def test_processable_registry_entries_excludes_disabled_mode():
    entries = processable_registry_entries()

    assert len(entries) == 31
    assert all(entry.mode != "disabled" for entry in entries)


def _stub_freshness(entry) -> RepositoryFreshnessV1:
    org_repo = f"{entry.repo_url.rsplit('/', 2)[-2]}/{entry.repo_name}"
    return RepositoryFreshnessV1(
        org_repo=org_repo,
        family=entry.family,
        platform=entry.platform,
        live_source_revision="a" * 40,
        knowledge_repo_sha="a" * 40,
        freshness="current",
        live_probe_succeeded=True,
    )


def _minimal_facts(org_repo: str):
    source = FactSourceV2(
        source_type="mechanical_repository",
        location=f"repository://{org_repo}",
        source_revision="a" * 40,
    )
    fact = FactRecordV2(
        fact_id="product.capabilities:test",
        field="product.capabilities",
        value=["Exports widgets"],
        source=source,
        verification_state="verified",
        authoritative_owner="repository",
        confidence=1.0,
        affected_surfaces=["readme.capabilities"],
    )
    return resolve_product_facts(org_repo, [fact], missing_source=source, missing_field_surfaces={})


def test_portfolio_facts_readiness_never_fabricates_a_verdict_for_missing_facts():
    """A repository with no supplied facts is reported in
    `facts_not_collected`, never given a fabricated READY/BLOCKED verdict
    and never silently dropped from `total_processable`."""

    result = portfolio_facts_readiness(freshness_probe=_stub_freshness)

    assert result.total_processable == 31
    assert len(result.readiness) == 0
    assert len(result.facts_not_collected) == 31


def test_portfolio_facts_readiness_reports_supplied_facts():
    entries = processable_registry_entries()
    target = entries[0]
    org_repo = f"{target.repo_url.rsplit('/', 2)[-2]}/{target.repo_name}"

    result = portfolio_facts_readiness(
        freshness_probe=_stub_freshness,
        facts_by_org_repo={org_repo: _minimal_facts(org_repo)},
    )

    assert result.total_processable == 31
    assert len(result.readiness) == 1
    assert result.readiness[0].org_repo == org_repo
    assert org_repo not in result.facts_not_collected
    assert len(result.facts_not_collected) == 30


def test_portfolio_facts_readiness_freshness_covers_every_processable_entry():
    result = portfolio_facts_readiness(freshness_probe=_stub_freshness)

    assert len(result.freshness) == 31
    assert all(row.freshness == "current" for row in result.freshness)
