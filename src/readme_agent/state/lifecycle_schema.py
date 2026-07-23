"""Versioned trigger, checkpoint, and health contracts for restartable runs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

TriggerEventTypeV2 = Literal[
    "schedule",
    "workflow_dispatch",
    "workflow_call",
    "repository_dispatch",
    "operator_request",
    "cli_manual",
]
TriggerStatusV2 = Literal[
    "accepted",
    "processing",
    "blocked",
    "retryable",
    "failed",
    "completed",
    "deduplicated",
]
CheckpointStageV1 = Literal[
    "trigger_accepted",
    "run_started",
    "snapshot_captured",
    "profile_completed",
    "task_started",
    "task_completed",
    "verifier_result",
    "repair_plan",
    "effect_pending",
    "effect_applied",
    "final_acceptance",
]
FailureClassificationV1 = Literal[
    "transient",
    "permanent",
    "state_unavailable",
    "rate_limited",
    "authorization_blocked",
    "validation_failed",
    "unsupported",
    "unknown",
]


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class TriggerEnvelopeV2(BaseModel):
    """Normalized identity for every production trigger source."""

    schema_version: Literal[2] = 2
    provider_event_id: str
    event_type: TriggerEventTypeV2
    repository_scope: str
    delivery_id: str | None = None
    workflow_run_id: str | None = None
    source_revision: str | None = None
    schedule_window: str | None = None
    occurred_at: str = Field(default_factory=utc_now_iso)
    dedup_key: str

    @field_validator("provider_event_id", "repository_scope", "dedup_key")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("repository_scope")
    @classmethod
    def _repository_shape(cls, value: str) -> str:
        if value.startswith("mission/"):
            return value
        if value.count("/") != 1 or any(not part for part in value.split("/")):
            raise ValueError("repository_scope must look like 'org/repo'")
        return value

    @model_validator(mode="after")
    def _schedule_has_window(self) -> TriggerEnvelopeV2:
        if self.event_type == "schedule" and not self.schedule_window:
            raise ValueError("schedule triggers require schedule_window")
        return self


class TriggerLifecycleV2(BaseModel):
    """Mutable processing state for one immutable trigger envelope."""

    envelope: TriggerEnvelopeV2
    status: TriggerStatusV2 = "accepted"
    accepted_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    lease_expires_at: str | None = None
    failure_classification: FailureClassificationV1 | None = None
    failure_detail: str | None = None
    recovery_count: int = Field(default=0, ge=0)
    last_checkpoint_id: str | None = None


class CheckpointV1(BaseModel):
    """One immutable lifecycle boundary persisted before later work proceeds."""

    schema_version: Literal[1] = 1
    checkpoint_id: str
    trigger_dedup_key: str
    run_id: str
    repository: str
    stage: CheckpointStageV1
    task_id: str | None = None
    action: str | None = None
    attempt: int = Field(default=1, ge=1)
    input_hash: str | None = None
    output_hash: str | None = None
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str = Field(default_factory=utc_now_iso)
    failure_classification: FailureClassificationV1 | None = None
    detail: str | None = None

    @field_validator("checkpoint_id", "trigger_dedup_key", "run_id", "repository")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class RecoveryCandidateV1(BaseModel):
    repository: str
    trigger_dedup_key: str
    prior_status: TriggerStatusV2
    last_checkpoint_id: str | None = None
    recovery_count: int
    reason: str


class HealthReportV1(BaseModel):
    """Portfolio health derived only from durable lifecycle state."""

    schema_version: Literal[1] = 1
    generated_at: str = Field(default_factory=utc_now_iso)
    repositories_checked: int = Field(ge=0)
    missed_schedule_windows: list[dict] = Field(default_factory=list)
    backlog: list[dict] = Field(default_factory=list)
    stale_leases: list[dict] = Field(default_factory=list)
    repeated_failures: list[dict] = Field(default_factory=list)
    rate_limit_state: dict[str, dict] = Field(default_factory=dict)
    evidence_failures: list[dict] = Field(default_factory=list)
    open_proposals: list[dict] = Field(default_factory=list)
    last_success: dict[str, str | None] = Field(default_factory=dict)
    state_failures: list[dict] = Field(default_factory=list)
    healthy: bool
