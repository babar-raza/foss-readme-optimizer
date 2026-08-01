"""Reconcile discovery observations to the allow-list by stable provider identity."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from readme_agent.errors import ConfigError
from readme_agent.registry.discovery_models import DiscoveryInventoryV1, DiscoveryObservationV1
from readme_agent.registry.models import ProductEntry
from readme_agent.registry.naming import (
    classify_managed_repository_name,
    validate_managed_repository_coordinates,
)
from readme_agent.registry.reconciliation_models import (
    ReconciliationAction,
    RegistryReconciliationRecordV1,
    RegistryReconciliationResultV1,
)

_REFRESHED_FIELDS = ("repo_name", "repo_url", "clone_url", "active", "discovered_via")


def reconcile_registry(
    existing: list[dict[str, Any]],
    inventory: DiscoveryInventoryV1,
) -> RegistryReconciliationResultV1:
    """Reconcile every observation without using family/platform as identity."""

    entries = [dict(item) for item in existing]
    _validate_existing_entries(entries)
    by_repository_id = {
        int(item["provider_identity"]["repository_id"]): index
        for index, item in enumerate(entries)
        if item.get("provider_identity") is not None
    }
    legacy_by_full_name: dict[str, list[int]] = {}
    for index, item in enumerate(entries):
        if item.get("provider_identity") is None:
            legacy_by_full_name.setdefault(_entry_full_name(item).casefold(), []).append(index)

    records: list[RegistryReconciliationRecordV1] = []
    excluded_existing_repository_ids: set[int] = set()
    seen_observation_ids: set[int] = set()
    seen_node_ids: set[str] = set()
    for observation in sorted(
        inventory.observations,
        key=lambda item: (item.provider_repository_id, item.full_name.casefold()),
    ):
        repository_id = int(observation.provider_repository_id)
        if repository_id in seen_observation_ids:
            raise ConfigError(f"duplicate observed provider repository ID {repository_id}")
        if observation.provider_node_id in seen_node_ids:
            raise ConfigError(
                f"duplicate observed provider node ID {observation.provider_node_id!r}"
            )
        seen_observation_ids.add(repository_id)
        seen_node_ids.add(observation.provider_node_id)

        existing_index = by_repository_id.get(repository_id)
        if existing_index is not None:
            existing_identity = entries[existing_index]["provider_identity"]
            if existing_identity["node_id"] != observation.provider_node_id:
                raise ConfigError(
                    f"provider node ID changed for repository ID {repository_id}: "
                    f"{existing_identity['node_id']!r} -> {observation.provider_node_id!r}"
                )
            prior_full_name = _entry_full_name(entries[existing_index])
            if observation.classification != "matched":
                name_is_nonconforming = classify_managed_repository_name(observation.name) is None
                if not name_is_nonconforming:
                    held_action: ReconciliationAction = (
                        "held_ambiguous"
                        if observation.classification == "ambiguous"
                        else "held_unmatched"
                    )
                    records.append(
                        _record(
                            observation,
                            action=held_action,
                            prior_full_name=prior_full_name,
                            reason=(
                                "a conforming admitted identity has unresolved classification; "
                                "retain its prior registry entry without refreshing it"
                            ),
                        )
                    )
                    continue
                excluded_existing_repository_ids.add(repository_id)
                records.append(
                    _record(
                        observation,
                        action="excluded_nonconforming",
                        prior_full_name=prior_full_name,
                        reason=(
                            "an admitted provider identity no longer satisfies the required "
                            "repository naming contract"
                        ),
                    )
                )
                continue
            entries[existing_index] = _refresh_entry(entries[existing_index], observation)
            records.append(
                _record(
                    observation,
                    action="refreshed",
                    prior_full_name=prior_full_name,
                    resulting_full_name=_entry_full_name(entries[existing_index]),
                    reason="stable provider repository ID matched an admitted entry",
                )
            )
            continue

        legacy_matches = legacy_by_full_name.get(observation.full_name.casefold(), [])
        if len(legacy_matches) > 1:
            raise ConfigError(
                f"ambiguous legacy registry identity for {observation.full_name!r}: "
                f"{len(legacy_matches)} entries"
            )
        if len(legacy_matches) == 1:
            existing_index = legacy_matches[0]
            prior_full_name = _entry_full_name(entries[existing_index])
            entries[existing_index] = _refresh_entry(entries[existing_index], observation)
            by_repository_id[repository_id] = existing_index
            records.append(
                _record(
                    observation,
                    action="migrated",
                    prior_full_name=prior_full_name,
                    resulting_full_name=_entry_full_name(entries[existing_index]),
                    reason=(
                        "one exact legacy full-name match was upgraded to stable provider identity"
                    ),
                )
            )
            continue

        if observation.classification == "matched":
            entries.append(_new_disabled_entry(observation, entries))
            by_repository_id[repository_id] = len(entries) - 1
            records.append(
                _record(
                    observation,
                    action="admitted_disabled",
                    resulting_full_name=observation.full_name,
                    reason="matched observation had no admitted stable or legacy identity",
                )
            )
            continue

        action: ReconciliationAction = (
            "held_ambiguous" if observation.classification == "ambiguous" else "held_unmatched"
        )
        records.append(
            _record(
                observation,
                action=action,
                reason=(
                    "non-matching observation remains discovery-only pending explicit disposition"
                ),
            )
        )

    entries = [
        entry
        for entry in entries
        if entry.get("provider_identity") is None
        or int(entry["provider_identity"]["repository_id"]) not in excluded_existing_repository_ids
    ]
    _validate_existing_entries(entries)
    entries.sort(key=_entry_sort_key)
    return RegistryReconciliationResultV1(
        inventory_complete=inventory.complete,
        entries=entries,
        records=records,
    )


def _validate_existing_entries(entries: list[dict[str, Any]]) -> None:
    validated = [ProductEntry.model_validate(item) for item in entries]
    for entry in validated:
        try:
            validate_managed_repository_coordinates(
                entry.repo_name,
                entry.family,
                entry.platform,
            )
        except ValueError as exc:
            raise ConfigError(f"ineligible registry entry {entry.org_repo}: {exc}") from exc
    validate_stable_identities(validated)


def validate_stable_identities(entries: Iterable[ProductEntry]) -> None:
    """Fail closed when two admitted entries claim the same provider identity."""

    entries = list(entries)
    repository_ids = [
        int(entry.provider_identity.repository_id)
        for entry in entries
        if entry.provider_identity is not None
    ]
    node_ids = [
        entry.provider_identity.node_id for entry in entries if entry.provider_identity is not None
    ]
    duplicate_repository_ids = sorted(
        value for value, count in Counter(repository_ids).items() if count > 1
    )
    duplicate_node_ids = sorted(value for value, count in Counter(node_ids).items() if count > 1)
    if duplicate_repository_ids:
        raise ConfigError(f"duplicate provider repository IDs: {duplicate_repository_ids}")
    if duplicate_node_ids:
        raise ConfigError(f"duplicate provider node IDs: {duplicate_node_ids}")


def _entry_full_name(entry: dict[str, Any]) -> str:
    path = urlparse(str(entry["repo_url"])).path.strip("/")
    parts = path.split("/")
    if len(parts) < 2:
        raise ConfigError(f"registry repo_url has no owner/name: {entry['repo_url']!r}")
    return f"{parts[0]}/{entry['repo_name']}"


def _refresh_entry(
    entry: dict[str, Any],
    observation: DiscoveryObservationV1,
) -> dict[str, Any]:
    refreshed = dict(entry)
    observed = {
        "repo_name": observation.name,
        "repo_url": observation.html_url,
        "clone_url": observation.clone_url,
        "active": not observation.archived,
        "discovered_via": "github",
    }
    for field in _REFRESHED_FIELDS:
        refreshed[field] = observed[field]
    if observation.classification == "matched":
        assert observation.family is not None
        assert observation.platform is not None
        refreshed["family"] = observation.family
        refreshed["platform"] = observation.platform
    refreshed["registry_schema_version"] = 2
    refreshed["provider_identity"] = {
        "schema_version": 1,
        "provider": observation.provider,
        "repository_id": observation.provider_repository_id,
        "node_id": observation.provider_node_id,
    }
    return refreshed


def _new_disabled_entry(
    observation: DiscoveryObservationV1,
    existing_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    entry = observation.to_registry_entry()
    inherited_profiles = {
        (item.get("ecosystem"), item.get("policy_profile"))
        for item in existing_entries
        if item.get("family") == observation.family
        and item.get("platform") == observation.platform
        and item.get("ecosystem") is not None
        and item.get("policy_profile") is not None
    }
    ecosystem = None
    policy_profile = None
    if len(inherited_profiles) == 1:
        ecosystem, policy_profile = next(iter(inherited_profiles))
    entry.update(
        {
            "registry_schema_version": 2,
            "provider_identity": {
                "schema_version": 1,
                "provider": observation.provider,
                "repository_id": observation.provider_repository_id,
                "node_id": observation.provider_node_id,
            },
            "mode": "disabled",
            "ecosystem": ecosystem,
            "policy_profile": policy_profile,
        }
    )
    return entry


def _record(
    observation: DiscoveryObservationV1,
    *,
    action: ReconciliationAction,
    reason: str,
    prior_full_name: str | None = None,
    resulting_full_name: str | None = None,
) -> RegistryReconciliationRecordV1:
    return RegistryReconciliationRecordV1(
        provider_repository_id=observation.provider_repository_id,
        provider_node_id=observation.provider_node_id,
        observation_full_name=observation.full_name,
        classification=observation.classification,
        action=action,
        prior_full_name=prior_full_name,
        resulting_full_name=resulting_full_name,
        reason=reason,
    )


def _entry_sort_key(entry: dict[str, Any]) -> tuple[str, str, int, str]:
    identity = entry.get("provider_identity")
    repository_id = int(identity["repository_id"]) if identity is not None else 0
    return (
        str(entry["family"]).casefold(),
        str(entry["platform"]).casefold(),
        repository_id,
        _entry_full_name(entry).casefold(),
    )
