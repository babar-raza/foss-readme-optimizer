"""Typed contracts for stable-identity registry reconciliation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

ReconciliationAction = Literal[
    "migrated",
    "refreshed",
    "admitted_disabled",
    "held_unmatched",
    "held_ambiguous",
]


class RegistryReconciliationRecordV1(BaseModel):
    """One observation's deterministic reconciliation disposition."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    provider: Literal["github"] = "github"
    provider_repository_id: StrictInt = Field(gt=0)
    provider_node_id: str = Field(min_length=1)
    observation_full_name: str = Field(min_length=1)
    classification: Literal["matched", "ambiguous", "unmatched"]
    action: ReconciliationAction
    prior_full_name: str | None = None
    resulting_full_name: str | None = None
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def admitted_actions_have_a_result(self) -> RegistryReconciliationRecordV1:
        admitted = self.action in {"migrated", "refreshed", "admitted_disabled"}
        if admitted != (self.resulting_full_name is not None):
            raise ValueError("admitted actions require one resulting full name")
        return self


class RegistryReconciliationResultV1(BaseModel):
    """Reconciled allow-list plus a complete observation ledger."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    inventory_complete: bool
    entries: list[dict[str, Any]]
    records: list[RegistryReconciliationRecordV1]

    @model_validator(mode="after")
    def every_observation_has_one_record(self) -> RegistryReconciliationResultV1:
        identities = [record.provider_repository_id for record in self.records]
        if len(identities) != len(set(identities)):
            raise ValueError(
                "each provider repository ID must have exactly one reconciliation record"
            )
        return self
