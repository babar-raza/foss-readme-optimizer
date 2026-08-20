"""Registry-derived cohort resolution: 33->31+2, seven-canary resolution, filters, fleet-remaining.

Proves the task's own acceptance bullets: "33 rows resolve to 31 processable plus two generic
terminal skips" (via the real registry -- see the `_classify_tree_processability` fixtures in
`test_registry_intake.py` for the processability half) and "seven-canary selection is
registry-derived."
"""

from __future__ import annotations

import pytest

from readme_agent.supervisor.portfolio_proof_engine.registry_cohort import (
    SEVEN_CANARY_PAIRS,
    CanaryResolutionError,
    filter_entries,
    load_portfolio_entries,
    resolve_fleet_remaining,
    resolve_seven_canaries,
)
from tests.unit.portfolio_proof_engine_fixtures import make_entry


def _fixture_registry():
    return [
        make_entry(org_repo=f"acme/{family}-{platform}", family=family, platform=platform)
        for family, platform in SEVEN_CANARY_PAIRS
    ] + [make_entry(org_repo="acme/extra-widget", family="widgets", platform="python")]


def test_resolve_seven_canaries_matches_every_configured_pair():
    entries = _fixture_registry()
    cohort = resolve_seven_canaries(entries)
    assert len(cohort) == len(SEVEN_CANARY_PAIRS)
    assert [(entry.family, entry.platform) for entry in cohort] == list(SEVEN_CANARY_PAIRS)


def test_resolve_seven_canaries_never_hardcodes_an_org_repo():
    entries = _fixture_registry()
    cohort = resolve_seven_canaries(entries)
    # Every resolved member's identity is derived from the registry fixture, not this test's
    # knowledge of a specific org/repo string.
    fixture_org_repos = {entry.org_repo for entry in entries}
    assert {entry.org_repo for entry in cohort} <= fixture_org_repos


def test_resolve_seven_canaries_fails_loudly_when_a_pair_is_missing():
    entries = _fixture_registry()[1:]  # drop the first configured canary pair
    with pytest.raises(CanaryResolutionError):
        resolve_seven_canaries(entries)


def test_resolve_seven_canaries_against_the_real_registry():
    """The real `data/products.json` must carry all seven configured (family, platform) pairs --
    this is the actual acceptance proof, not just the synthetic fixture above."""

    entries = load_portfolio_entries()
    cohort = resolve_seven_canaries(entries)
    assert len(cohort) == 7


def test_real_registry_has_exactly_33_rows():
    assert len(load_portfolio_entries()) == 33


def test_filter_entries_by_only():
    entries = _fixture_registry()
    filtered = filter_entries(entries, only=[entries[0].org_repo, entries[2].org_repo])
    assert {entry.org_repo for entry in filtered} == {entries[0].org_repo, entries[2].org_repo}


def test_filter_entries_by_platform_and_family():
    entries = _fixture_registry()
    filtered = filter_entries(entries, platform="python")
    assert all(entry.platform == "python" for entry in filtered)
    filtered = filter_entries(entries, family="cells")
    assert all(entry.family == "cells" for entry in filtered)


def test_filter_entries_with_no_filters_returns_everything():
    entries = _fixture_registry()
    assert filter_entries(entries) == entries


def test_resolve_fleet_remaining_excludes_accepted():
    entries = _fixture_registry()
    accepted = {entries[0].org_repo, entries[1].org_repo}
    remaining = resolve_fleet_remaining(entries, accepted)
    assert accepted.isdisjoint({entry.org_repo for entry in remaining})
    assert len(remaining) == len(entries) - len(accepted)
