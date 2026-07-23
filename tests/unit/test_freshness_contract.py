"""`FRESH-001`-`006` (Wave 9.7): per-surface freshness for the four non-git-
tracked domains (`GITHUB_GENERATED_SURFACE_AUDIT`/`PACKAGE_RELEASE_AUDIT`/
`METADATA_PRESENTATION`/`VISUAL_PREPARATION`) -- README/community files stay
covered by the existing git-SHA comparison, unaffected by this module."""

from datetime import UTC, datetime, timedelta

from readme_agent.capabilities.domains import (
    GITHUB_GENERATED_SURFACE_AUDIT,
    METADATA_PRESENTATION,
    PACKAGE_RELEASE_AUDIT,
    VISUAL_PREPARATION,
)
from readme_agent.state.freshness_contract import (
    DEFAULT_SURFACE_CONTRACTS,
    any_surface_due_for_recheck,
    is_due_for_recheck,
    refresh_surface_contracts,
)
from readme_agent.state.schema import SurfaceFreshnessContractV1

NOW = datetime(2026, 7, 23, 12, 0, 0, tzinfo=UTC)


class TestDefaultSurfaceContracts:
    def test_covers_exactly_the_four_non_git_tracked_domains(self):
        assert set(DEFAULT_SURFACE_CONTRACTS) == {
            GITHUB_GENERATED_SURFACE_AUDIT,
            PACKAGE_RELEASE_AUDIT,
            METADATA_PRESENTATION,
            VISUAL_PREPARATION,
        }

    def test_every_default_contract_starts_unchecked(self):
        assert all(c.last_checked_at is None for c in DEFAULT_SURFACE_CONTRACTS.values())


class TestIsDueForRecheck:
    def test_none_contract_is_due(self):
        assert is_due_for_recheck(None, NOW)

    def test_never_checked_contract_is_due(self):
        contract = SurfaceFreshnessContractV1(
            surface_id="x", authoritative_source="github_api", ttl_seconds=3600
        )
        assert is_due_for_recheck(contract, NOW)

    def test_checked_within_ttl_is_not_due(self):
        contract = SurfaceFreshnessContractV1(
            surface_id="x",
            authoritative_source="github_api",
            ttl_seconds=3600,
            last_checked_at=(NOW - timedelta(seconds=60)).isoformat(),
        )
        assert not is_due_for_recheck(contract, NOW)

    def test_checked_past_ttl_is_due(self):
        contract = SurfaceFreshnessContractV1(
            surface_id="x",
            authoritative_source="github_api",
            ttl_seconds=3600,
            last_checked_at=(NOW - timedelta(hours=2)).isoformat(),
        )
        assert is_due_for_recheck(contract, NOW)

    def test_exactly_at_ttl_boundary_is_due(self):
        contract = SurfaceFreshnessContractV1(
            surface_id="x",
            authoritative_source="github_api",
            ttl_seconds=3600,
            last_checked_at=(NOW - timedelta(seconds=3600)).isoformat(),
        )
        assert is_due_for_recheck(contract, NOW)


class TestAnySurfaceDueForRecheck:
    def _all_fresh_contracts(self):
        return {
            surface_id: contract.model_copy(update={"last_checked_at": NOW.isoformat()})
            for surface_id, contract in DEFAULT_SURFACE_CONTRACTS.items()
        }

    def test_empty_contracts_dict_is_due(self):
        assert any_surface_due_for_recheck({}, NOW)

    def test_all_freshly_checked_is_not_due(self):
        assert not any_surface_due_for_recheck(self._all_fresh_contracts(), NOW)

    def test_one_stale_surface_among_fresh_ones_is_due(self):
        contracts = self._all_fresh_contracts()
        stale = contracts[PACKAGE_RELEASE_AUDIT].model_copy(
            update={"last_checked_at": (NOW - timedelta(days=1)).isoformat()}
        )
        contracts[PACKAGE_RELEASE_AUDIT] = stale
        assert any_surface_due_for_recheck(contracts, NOW)


class TestRefreshSurfaceContracts:
    def test_stamps_every_tracked_surface_as_checked_now(self):
        refreshed = refresh_surface_contracts({}, {}, NOW)
        assert set(refreshed) == set(DEFAULT_SURFACE_CONTRACTS)
        assert all(c.last_checked_at == NOW.isoformat() for c in refreshed.values())

    def test_records_the_given_observed_hash_per_surface(self):
        refreshed = refresh_surface_contracts({}, {METADATA_PRESENTATION: "hash-abc"}, NOW)
        assert refreshed[METADATA_PRESENTATION].observed_hash == "hash-abc"
        assert refreshed[PACKAGE_RELEASE_AUDIT].observed_hash is None

    def test_carries_forward_a_prior_contracts_own_ttl_rather_than_resetting_it(self):
        prior = {
            METADATA_PRESENTATION: SurfaceFreshnessContractV1(
                surface_id=METADATA_PRESENTATION,
                authoritative_source="github_api",
                ttl_seconds=999,
                last_checked_at=(NOW - timedelta(hours=5)).isoformat(),
                observed_hash="old-hash",
            )
        }
        refreshed = refresh_surface_contracts(prior, {}, NOW)
        assert refreshed[METADATA_PRESENTATION].ttl_seconds == 999
        assert refreshed[METADATA_PRESENTATION].last_checked_at == NOW.isoformat()
