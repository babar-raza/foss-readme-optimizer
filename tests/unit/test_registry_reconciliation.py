from __future__ import annotations

from copy import deepcopy

import pytest

from readme_agent.errors import ConfigError
from readme_agent.registry.discovery_models import (
    DiscoveryInventoryV1,
    DiscoveryObservationV1,
    DiscoverySourceResultV1,
    DiscoverySourceV1,
)
from readme_agent.registry.models import ProductEntry
from readme_agent.registry.reconciliation import (
    reconcile_registry,
    validate_stable_identities,
)


def _observation(
    repository_id: int,
    full_name: str,
    *,
    family: str | None = "cells",
    platform: str | None = "java",
    classification: str = "matched",
    archived: bool = False,
    node_id: str | None = None,
) -> DiscoveryObservationV1:
    owner, name = full_name.split("/", maxsplit=1)
    return DiscoveryObservationV1(
        source_id=f"github-org:{owner}",
        provider_repository_id=repository_id,
        provider_node_id=node_id or f"R_{repository_id}",
        full_name=full_name,
        name=name,
        html_url=f"https://github.com/{full_name}",
        clone_url=f"https://github.com/{full_name}.git",
        visibility="public",
        default_branch="main",
        archived=archived,
        observed_at="2026-07-29T00:00:00Z",
        classification=classification,
        classification_reason="test observation",
        disposition="admit_candidate" if classification == "matched" else "review_required",
        family=family if classification == "matched" else None,
        platform=platform if classification == "matched" else None,
    )


def _inventory(*observations: DiscoveryObservationV1) -> DiscoveryInventoryV1:
    source = DiscoverySourceV1(
        source_id="github-org:aspose-cells-foss",
        organization="aspose-cells-foss",
        family_hint="cells",
    )
    return DiscoveryInventoryV1(
        captured_at="2026-07-29T00:00:00Z",
        sources=[
            DiscoverySourceResultV1(
                source=source,
                status="complete",
                observed_at="2026-07-29T00:00:00Z",
                observation_count=len(observations),
            )
        ],
        observations=list(observations),
        complete=True,
    )


def _legacy_entry(
    full_name: str = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
    *,
    family: str = "cells",
    platform: str = "java",
) -> dict:
    owner, name = full_name.split("/", maxsplit=1)
    return {
        "family": family,
        "platform": platform,
        "repo_name": name,
        "repo_url": f"https://github.com/{full_name}",
        "clone_url": f"https://github.com/{full_name}.git",
        "active": True,
        "discovered_via": "github",
        "overrides": {"maintainer_note": "preserve"},
        "mode": "full",
        "ecosystem": "maven",
        "policy_profile": "aspose-cells-foss",
    }


def _identified_entry(repository_id: int = 10, **kwargs) -> dict:
    entry = _legacy_entry(**kwargs)
    entry.update(
        {
            "registry_schema_version": 2,
            "provider_identity": {
                "schema_version": 1,
                "provider": "github",
                "repository_id": repository_id,
                "node_id": f"R_{repository_id}",
            },
        }
    )
    return entry


def test_exact_legacy_full_name_is_migrated_without_overwriting_owned_fields():
    existing = _legacy_entry()
    result = reconcile_registry(
        [existing],
        _inventory(_observation(10, "aspose-cells-foss/Aspose.Cells-FOSS-for-Java")),
    )

    assert len(result.entries) == 1
    migrated = result.entries[0]
    assert migrated["registry_schema_version"] == 2
    assert migrated["provider_identity"]["repository_id"] == 10
    assert migrated["mode"] == "full"
    assert migrated["ecosystem"] == "maven"
    assert migrated["policy_profile"] == "aspose-cells-foss"
    assert migrated["overrides"] == {"maintainer_note": "preserve"}
    assert result.records[0].action == "migrated"


def test_provider_repository_id_survives_rename_and_transfer():
    existing = _identified_entry()
    renamed = _observation(
        10,
        "transferred-owner/renamed-product",
        family=None,
        platform=None,
        classification="unmatched",
    )

    result = reconcile_registry([existing], _inventory(renamed))

    refreshed = result.entries[0]
    assert refreshed["repo_name"] == "renamed-product"
    assert refreshed["repo_url"] == "https://github.com/transferred-owner/renamed-product"
    assert refreshed["family"] == "cells"
    assert refreshed["platform"] == "java"
    assert refreshed["mode"] == "full"
    assert result.records[0].action == "refreshed"
    assert result.records[0].prior_full_name == ("aspose-cells-foss/Aspose.Cells-FOSS-for-Java")


def test_multiple_repositories_for_one_family_platform_are_retained():
    existing = _identified_entry(10)
    variant = _observation(
        11,
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Java-Experimental",
    )

    result = reconcile_registry([existing], _inventory(variant))

    assert len(result.entries) == 2
    assert {(item["family"], item["platform"]) for item in result.entries} == {("cells", "java")}
    assert {item["provider_identity"]["repository_id"] for item in result.entries} == {10, 11}
    admitted = next(
        item for item in result.entries if item["provider_identity"]["repository_id"] == 11
    )
    assert admitted["mode"] == "disabled"
    assert admitted["ecosystem"] is None
    assert admitted["policy_profile"] is None


@pytest.mark.parametrize(
    ("classification", "expected_action"),
    [("unmatched", "held_unmatched"), ("ambiguous", "held_ambiguous")],
)
def test_nonmatching_observations_remain_discovery_only(classification, expected_action):
    observation = _observation(
        12,
        "aspose-cells-foss/custom-repository",
        family=None,
        platform=None,
        classification=classification,
    )

    result = reconcile_registry([], _inventory(observation))

    assert result.entries == []
    assert result.records[0].action == expected_action
    assert result.records[0].resulting_full_name is None


def test_archived_observation_refreshes_activity_without_changing_policy():
    result = reconcile_registry(
        [_identified_entry()],
        _inventory(
            _observation(
                10,
                "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
                archived=True,
            )
        ),
    )

    assert result.entries[0]["active"] is False
    assert result.entries[0]["mode"] == "full"
    assert result.entries[0]["policy_profile"] == "aspose-cells-foss"


def test_input_permutation_does_not_change_entries_or_ledger():
    observations = [
        _observation(30, "aspose-cells-foss/Aspose.Cells-FOSS-for-Java-Three"),
        _observation(20, "aspose-cells-foss/Aspose.Cells-FOSS-for-Java-Two"),
    ]

    forward = reconcile_registry([], _inventory(*observations))
    reverse = reconcile_registry([], _inventory(*reversed(observations)))

    assert forward.entries == reverse.entries
    assert forward.records == reverse.records


def test_identical_schema_v2_rerun_is_an_entry_no_op():
    existing = _identified_entry(10)
    observation = _observation(
        10,
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
    )

    result = reconcile_registry([existing], _inventory(observation))

    assert result.entries == [existing]
    assert result.records[0].action == "refreshed"


def test_duplicate_observed_repository_id_fails_closed():
    with pytest.raises(ConfigError, match="duplicate observed provider repository ID"):
        reconcile_registry(
            [],
            _inventory(
                _observation(10, "aspose-cells-foss/one"),
                _observation(10, "aspose-cells-foss/two"),
            ),
        )


def test_provider_node_id_change_for_same_repository_id_fails_closed():
    with pytest.raises(ConfigError, match="provider node ID changed"):
        reconcile_registry(
            [_identified_entry(10)],
            _inventory(
                _observation(
                    10,
                    "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
                    node_id="R_DIFFERENT",
                )
            ),
        )


def test_duplicate_admitted_stable_identity_fails_closed():
    duplicate = deepcopy(_identified_entry(10))
    duplicate["repo_name"] = "duplicate"
    duplicate["repo_url"] = "https://github.com/aspose-cells-foss/duplicate"
    duplicate["clone_url"] = "https://github.com/aspose-cells-foss/duplicate.git"

    with pytest.raises(ConfigError, match="duplicate provider repository IDs"):
        reconcile_registry([_identified_entry(10), duplicate], _inventory())


def test_registry_schema_v2_requires_provider_identity():
    entry = _legacy_entry()
    entry["registry_schema_version"] = 2

    with pytest.raises(ValueError, match="provider_identity"):
        ProductEntry.model_validate(entry)


def test_public_identity_validator_rejects_duplicate_node_ids():
    first = ProductEntry.model_validate(_identified_entry(10))
    second_raw = _identified_entry(
        11,
        full_name="aspose-cells-foss/Aspose.Cells-FOSS-for-Java-Two",
    )
    second_raw["provider_identity"]["node_id"] = "R_10"
    second = ProductEntry.model_validate(second_raw)

    with pytest.raises(ConfigError, match="duplicate provider node IDs"):
        validate_stable_identities([first, second])
