"""Build and verify immutable registry revisions for portfolio admission."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent import env
from readme_agent.evidence.redaction import redact
from readme_agent.registry.discovery_models import DiscoveryInventoryV1
from readme_agent.registry.reconciliation_models import RegistryReconciliationResultV1


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _entry_full_name(entry: dict[str, Any]) -> str:
    owner = str(entry["repo_url"]).rstrip("/").split("/")[-2]
    return f"{owner}/{entry['repo_name']}"


def _observation_payload(observation: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in observation.items()
        if key not in {"observed_at", "schema_version"}
    }


class RegistryObservationChangeV1(BaseModel):
    """One meaningful provider observation change eligible for intake."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    provider_repository_id: int = Field(gt=0)
    org_repo: str
    change_kind: Literal["added", "renamed", "archived", "refreshed"]
    observation_revision: str = Field(pattern=r"^[0-9a-f]{64}$")


class RegistryRevisionV1(BaseModel):
    """One source, observation, reconciliation, and allow-list snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    revision_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    captured_at: str
    fresh_until: str
    source_catalog_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    products_registry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    reconciliation_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    admitted_repositories: list[str]
    observation_revisions: dict[str, str]
    additions: list[str] = Field(default_factory=list)
    renames: list[dict[str, str]] = Field(default_factory=list)
    archives: list[str] = Field(default_factory=list)
    exclusions: list[dict[str, str]] = Field(default_factory=list)
    source_failures: list[dict[str, str]] = Field(default_factory=list)
    observation_changes: list[RegistryObservationChangeV1] = Field(default_factory=list)
    pending_intake: list[str] = Field(default_factory=list)
    unexplained_observations: list[str] = Field(default_factory=list)
    complete: bool

    @model_validator(mode="after")
    def _identity_matches_content(self) -> RegistryRevisionV1:
        if self.revision_id != registry_revision_identity(self):
            raise ValueError("registry revision identity does not match its content")
        if self.complete == bool(self.source_failures):
            raise ValueError("complete must be true exactly when source_failures is empty")
        return self


def registry_revision_identity(revision: RegistryRevisionV1 | dict[str, Any]) -> str:
    payload = (
        revision.model_dump(mode="json", exclude={"revision_id"})
        if isinstance(revision, RegistryRevisionV1)
        else {key: value for key, value in revision.items() if key != "revision_id"}
    )
    return _canonical_sha256(payload)


def build_registry_revision(
    inventory: DiscoveryInventoryV1,
    reconciliation: RegistryReconciliationResultV1,
    *,
    previous_entries: list[dict[str, Any]],
    prior_revision: RegistryRevisionV1 | None = None,
    freshness_ttl: timedelta = timedelta(days=1),
    pending_intake: list[str] | None = None,
) -> RegistryRevisionV1:
    """Derive one deterministic revision from the complete reconciliation boundary."""

    source_catalog = [
        source.source.model_dump(mode="json")
        for source in sorted(inventory.sources, key=lambda item: item.source.source_id)
    ]
    observations = [
        observation.model_dump(mode="json")
        for observation in sorted(
            inventory.observations,
            key=lambda item: (item.provider_repository_id, item.full_name.casefold()),
        )
    ]
    observation_revisions = {
        str(item["provider_repository_id"]): _canonical_sha256(_observation_payload(item))
        for item in observations
    }
    prior_observation_revisions = prior_revision.observation_revisions if prior_revision else {}
    prior_by_id = {
        int(item["provider_identity"]["repository_id"]): item
        for item in previous_entries
        if item.get("provider_identity") is not None
    }
    resulting_by_id = {
        int(item["provider_identity"]["repository_id"]): item
        for item in reconciliation.entries
        if item.get("provider_identity") is not None
    }

    additions: list[str] = []
    renames: list[dict[str, str]] = []
    archives: list[str] = []
    exclusions: list[dict[str, str]] = []
    unexplained: list[str] = []
    changes: list[RegistryObservationChangeV1] = []
    for record in reconciliation.records:
        identity = str(record.provider_repository_id)
        observation_revision = observation_revisions[identity]
        if record.action == "admitted_disabled":
            assert record.resulting_full_name is not None
            additions.append(record.resulting_full_name)
            changes.append(
                RegistryObservationChangeV1(
                    provider_repository_id=record.provider_repository_id,
                    org_repo=record.resulting_full_name,
                    change_kind="added",
                    observation_revision=observation_revision,
                )
            )
            continue
        if record.action in {"held_unmatched", "held_ambiguous"}:
            exclusions.append(
                {
                    "org_repo": record.observation_full_name,
                    "classification": record.classification,
                    "reason": record.reason,
                }
            )
            unexplained.append(record.observation_full_name)
            continue
        assert record.resulting_full_name is not None
        previous = prior_by_id.get(record.provider_repository_id)
        current = resulting_by_id.get(record.provider_repository_id)
        if record.prior_full_name and record.prior_full_name != record.resulting_full_name:
            renames.append({"from": record.prior_full_name, "to": record.resulting_full_name})
            changes.append(
                RegistryObservationChangeV1(
                    provider_repository_id=record.provider_repository_id,
                    org_repo=record.resulting_full_name,
                    change_kind="renamed",
                    observation_revision=observation_revision,
                )
            )
        elif (
            previous is not None
            and current is not None
            and previous.get("active")
            and not current.get("active")
        ):
            archives.append(record.resulting_full_name)
            changes.append(
                RegistryObservationChangeV1(
                    provider_repository_id=record.provider_repository_id,
                    org_repo=record.resulting_full_name,
                    change_kind="archived",
                    observation_revision=observation_revision,
                )
            )
        elif (
            identity in prior_observation_revisions
            and prior_observation_revisions[identity] != observation_revision
        ):
            changes.append(
                RegistryObservationChangeV1(
                    provider_repository_id=record.provider_repository_id,
                    org_repo=record.resulting_full_name,
                    change_kind="refreshed",
                    observation_revision=observation_revision,
                )
            )

    source_failures = [
        {
            "source_id": failure.source.source_id,
            "organization": failure.source.organization,
            "error": redact(
                failure.error or "unknown source failure",
                env.secret_values(),
            ),
        }
        for failure in inventory.failures
    ]
    captured_at = _parse_utc(inventory.captured_at)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "revision_id": "0" * 64,
        "captured_at": captured_at.isoformat(),
        "fresh_until": (captured_at + freshness_ttl).isoformat(),
        "source_catalog_hash": _canonical_sha256(source_catalog),
        "observation_snapshot_hash": _canonical_sha256(
            [_observation_payload(item) for item in observations]
        ),
        "products_registry_hash": _canonical_sha256(reconciliation.entries),
        "reconciliation_hash": _canonical_sha256(
            [record.model_dump(mode="json") for record in reconciliation.records]
        ),
        "admitted_repositories": sorted(_entry_full_name(item) for item in reconciliation.entries),
        "observation_revisions": dict(sorted(observation_revisions.items())),
        "additions": sorted(additions),
        "renames": sorted(renames, key=lambda item: (item["from"], item["to"])),
        "archives": sorted(archives),
        "exclusions": sorted(exclusions, key=lambda item: item["org_repo"]),
        "source_failures": sorted(source_failures, key=lambda item: item["source_id"]),
        "observation_changes": [
            item.model_dump(mode="json")
            for item in sorted(changes, key=lambda item: item.provider_repository_id)
        ],
        "pending_intake": sorted(
            set(
                pending_intake
                if pending_intake is not None
                else [
                    *(prior_revision.pending_intake if prior_revision is not None else []),
                    *(item.org_repo for item in changes),
                ]
            )
        ),
        "unexplained_observations": sorted(unexplained),
        "complete": not source_failures,
    }
    payload["revision_id"] = registry_revision_identity(payload)
    return RegistryRevisionV1.model_validate(payload)


def with_pending_intake(
    revision: RegistryRevisionV1,
    pending_intake: list[str],
) -> RegistryRevisionV1:
    """Issue a new immutable revision after durable intake settlement."""

    payload = revision.model_dump(mode="json")
    payload["pending_intake"] = sorted(set(pending_intake))
    payload["revision_id"] = registry_revision_identity(payload)
    return RegistryRevisionV1.model_validate(payload)


def products_registry_hash(products: list[dict[str, Any]]) -> str:
    """Hash the exact admitted registry payload used by a campaign."""

    return _canonical_sha256(products)


def admitted_repository_names(products: list[dict[str, Any]]) -> list[str]:
    """Return the stable repository denominator represented by registry entries."""

    return sorted(_entry_full_name(item) for item in products)
