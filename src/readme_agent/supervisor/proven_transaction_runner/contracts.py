"""Typed contracts for the minimal proven-transaction runner."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProvenTransactionPhaseV1 = Literal[
    "OBSERVE_CURRENT_EXTERNAL_BLOCKS",
    "ADAPT_SMALLEST_RESOLVER_SEAM",
    "REPLAY_AFFECTED_FACT_STAGES",
    "REPLAY_SEALED_TRANSACTION",
]
ProvenTransactionActionV1 = Literal[
    "observe_current_external_blocks",
    "adapt_smallest_resolver_seam",
    "replay_affected_fact_stages",
    "replay_sealed_transaction",
]
RunnerPermissionV1 = Literal["read_only_local", "local_write"]
CheckpointStatusV1 = Literal["COMPLETED", "BLOCKED", "FAILED", "INTERRUPTED"]

PHASE_ORDER: tuple[ProvenTransactionPhaseV1, ...] = (
    "OBSERVE_CURRENT_EXTERNAL_BLOCKS",
    "ADAPT_SMALLEST_RESOLVER_SEAM",
    "REPLAY_AFFECTED_FACT_STAGES",
    "REPLAY_SEALED_TRANSACTION",
)


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RegisteredTransactionActionV1(_StrictFrozenModel):
    """One allow-listed action; product and remote effects are structurally absent."""

    action_id: ProvenTransactionActionV1
    phase: ProvenTransactionPhaseV1
    permission: RunnerPermissionV1
    input_model: str
    output_model: str
    retryable: bool
    product_effect_authority: Literal[False] = False


class ProvenTransactionContextV1(_StrictFrozenModel):
    """Stable identity of one PF04 transaction replay."""

    schema_version: Literal[1] = 1
    task_id: Literal["L8-PF-04-MINIMAL-GRAPH-RUNNER"]
    org_repo: str
    source_revision: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    graph_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dependency_hashes: dict[str, str] = Field(min_length=1)

    @field_validator("org_repo")
    @classmethod
    def _valid_org_repo(cls, value: str) -> str:
        if value.count("/") != 1 or any(not part for part in value.split("/")):
            raise ValueError("org_repo must look like 'org/repo'")
        return value

    @property
    def context_hash(self) -> str:
        return canonical_sha256(self.model_dump(mode="json"))


class ProvenTransactionActionInputV1(_StrictFrozenModel):
    """Input supplied to each registered action handler."""

    context: ProvenTransactionContextV1
    phase: ProvenTransactionPhaseV1
    action_id: ProvenTransactionActionV1
    attempt: int = Field(ge=1)
    prior_output_hashes: dict[str, str]


class ProvenTransactionActionResultV1(_StrictFrozenModel):
    """Bounded action result; handlers return evidence, never arbitrary commands."""

    status: Literal["COMPLETED", "BLOCKED"]
    output: dict
    evidence_refs: tuple[str, ...] = ()
    reason: str | None = None

    @model_validator(mode="after")
    def _blocked_has_reason(self) -> ProvenTransactionActionResultV1:
        if self.status == "BLOCKED" and not self.reason:
            raise ValueError("a blocked action requires a reason")
        return self


class ProvenTransactionCheckpointV1(_StrictFrozenModel):
    """One durable action attempt in the ordered transaction."""

    schema_version: Literal[1] = 1
    phase: ProvenTransactionPhaseV1
    action_id: ProvenTransactionActionV1
    attempt: int = Field(ge=1)
    context_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    status: CheckpointStatusV1
    evidence_refs: tuple[str, ...] = ()
    reason: str | None = None
    started_at: str
    completed_at: str

    @model_validator(mode="after")
    def _terminal_shape(self) -> ProvenTransactionCheckpointV1:
        if self.status == "COMPLETED" and self.output_hash is None:
            raise ValueError("a completed checkpoint requires output_hash")
        if self.status != "COMPLETED" and not self.reason:
            raise ValueError("a non-completed checkpoint requires a reason")
        return self


class ProvenTransactionReceiptV1(_StrictFrozenModel):
    """Append-only checkpoint history for one context-hashed transaction."""

    schema_version: Literal[1] = 1
    transaction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    context: ProvenTransactionContextV1
    registry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    checkpoints: tuple[ProvenTransactionCheckpointV1, ...] = ()
    terminal_status: Literal["IN_PROGRESS", "COMPLETED", "BLOCKED"] = "IN_PROGRESS"

    @model_validator(mode="after")
    def _identity_and_order(self) -> ProvenTransactionReceiptV1:
        if self.transaction_id != self.context.context_hash:
            raise ValueError("transaction_id must equal the context hash")
        phase_indexes = {phase: index for index, phase in enumerate(PHASE_ORDER)}
        completed: set[ProvenTransactionPhaseV1] = set()
        for checkpoint in self.checkpoints:
            if checkpoint.context_hash != self.context.context_hash:
                raise ValueError("checkpoint context does not match its receipt")
            if checkpoint.status == "COMPLETED":
                predecessors = PHASE_ORDER[: phase_indexes[checkpoint.phase]]
                if any(predecessor not in completed for predecessor in predecessors):
                    raise ValueError("checkpoint completed before its predecessor")
                completed.add(checkpoint.phase)
        if self.terminal_status == "COMPLETED" and completed != set(PHASE_ORDER):
            raise ValueError("completed receipt requires every ordered phase")
        return self


__all__ = [
    "PHASE_ORDER",
    "ProvenTransactionActionInputV1",
    "ProvenTransactionActionResultV1",
    "ProvenTransactionActionV1",
    "ProvenTransactionCheckpointV1",
    "ProvenTransactionContextV1",
    "ProvenTransactionPhaseV1",
    "ProvenTransactionReceiptV1",
    "RegisteredTransactionActionV1",
    "canonical_sha256",
    "utc_now_iso",
]
