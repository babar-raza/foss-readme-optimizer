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
# `RPOC-070` (sprint charter Part B.2 Phase 5 Lane S / Part C.7): one repo's
# overall README-POC pipeline progress -- a distinct dimension from
# `TriggerStatusV2` (one trigger event's processing lifecycle) and
# `CheckpointStageV1` (one run's restart boundaries). Transition legality for
# this vocabulary is enforced by `state/readme_poc_lifecycle.py`'s own
# transition table, the same "types live beside their siblings here, behavior
# lives in a dedicated module" split `TriggerStatusV2`/`state/lifecycle.py`
# already establish.
ReadmePocStatusV1 = Literal[
    "DISCOVERED",
    "SNAPSHOTTED",
    "PROFILED",
    "FACTS_COLLECTING",
    "FACTS_READY",
    "FACT_CONFLICT",
    "PLAN_READY",
    "CANDIDATE_GENERATED",
    "DETERMINISTIC_VALIDATION_FAILED",
    "AGENT_REVIEW_REJECTED",
    "REPAIRING",
    "AGENT_APPROVED",
    "HUMAN_REVIEW_READY",
    "HUMAN_ACCEPTED",
    "PR_ELIGIBLE",
    "PR_PROOF_COMPLETE",
]

# Version 2 is an in-place migration of the existing `readme_poc_lifecycle`
# slot, not a parallel progress store.  V1 omitted assessment, deterministic
# validation, active review, and no-op proof; it also conflated an unresolved
# fact with a resolved conflict.  The V2 vocabulary makes those gates
# observable before a portfolio metric can claim local approval.
ReadmePocStatusV2 = Literal[
    "DISCOVERED",
    "SNAPSHOTTED",
    "PROFILED",
    "FACTS_COLLECTING",
    "FACTS_READY",
    "README_ASSESSED",
    "PLAN_READY",
    "CANDIDATE_GENERATED",
    "DETERMINISTIC_VALIDATED",
    "AGENT_REVIEWING",
    "AGENT_APPROVED",
    "NO_OP_PROVEN",
    "HUMAN_REVIEW_READY",
    "HUMAN_ACCEPTED",
    "PR_ELIGIBLE",
    "PR_PROOF_COMPLETE",
    "BLOCKED_FACT_CONFLICT",
    "BLOCKED_MISSING_EVIDENCE",
    "SYSTEM_FAILURE",
    "DETERMINISTIC_VALIDATION_FAILED",
    "AGENT_REVIEW_REJECTED",
    "REPAIRING",
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


class ReadmePocTransitionV1(BaseModel):
    """One append-only entry in a repo's README-POC lifecycle history
    (`RPOC-070`) -- mirrors `state/schema.py::MissionTransitionV1`'s own
    shape (`from_status`/`to_status`/`observed_by`/`reason`/`evidence_refs`)
    one status dimension over, for the same reason: a transition worth
    persisting is always attributable and explained, never a bare status
    flip with no record of who/why."""

    from_status: ReadmePocStatusV1 | None = None
    to_status: ReadmePocStatusV1
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    observed_by: str
    occurred_at: str = Field(default_factory=utc_now_iso)


class ReadmePocLifecycleStateV1(BaseModel):
    """Durable per-org/repo README-POC pipeline-progress record (`RPOC-070`,
    sprint charter Part B.2 Phase 5 Lane S / Part C.7) -- one repo's overall
    position in the charter's discovery-through-PR-proof lifecycle, kept as
    its own slot on `RunStateV1`/`RunStateV2` (`readme_poc_lifecycle`), the
    same "own slot, never shared" convention `SupervisorStateV1`/
    `ProfileCacheV1`/`OpenProposalV1` already establish there.

    `status` defaults to `"DISCOVERED"` -- a repo with no persisted record
    yet (or one written before this field existed) is correctly read as "has
    not entered the README-POC pipeline," never a validation failure; see
    `state/readme_poc_lifecycle.py`'s migration test. `history` is
    append-only, written only via `state/readme_poc_lifecycle.py::
    transition_readme_poc_status()`, never mutated directly -- the same
    discipline `MissionExecutionStateV1.transition_history` already uses."""

    schema_version: Literal[1] = 1
    status: ReadmePocStatusV1 = "DISCOVERED"
    updated_at: str = Field(default_factory=utc_now_iso)
    history: list[ReadmePocTransitionV1] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)


class ReadmePocTransitionV2(BaseModel):
    """Append-only V2 transition with a fact/source revision binding."""

    from_status: ReadmePocStatusV2 | None = None
    to_status: ReadmePocStatusV2
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    observed_by: str
    occurred_at: str = Field(default_factory=utc_now_iso)
    source_revision: str | None = None


class ReadmePocLifecycleStateV2(BaseModel):
    """Current per-repository local-POC lifecycle in the existing state slot."""

    schema_version: Literal[2] = 2
    status: ReadmePocStatusV2 = "DISCOVERED"
    updated_at: str = Field(default_factory=utc_now_iso)
    history: list[ReadmePocTransitionV2] = Field(default_factory=list)
    source_revision: str | None = None
    facts_hash: str | None = None
    assessment_hash: str | None = None
    presentation_plan_hash: str | None = None
    candidate_hash: str | None = None
    prompt_hash: str | None = None
    reviewer_standard_hash: str | None = None
    protected_content_fingerprint: str | None = None
    repair_attempts_for_revision: int = Field(default=0, ge=0, le=2)
    details: dict = Field(default_factory=dict)


class HealthReportV1(BaseModel):
    """Portfolio health derived only from durable lifecycle state."""

    schema_version: Literal[1] = 1
    generated_at: str = Field(default_factory=utc_now_iso)
    repositories_checked: int = Field(ge=0)
    missed_schedule_windows: list[dict] = Field(default_factory=list)
    backlog: list[dict] = Field(default_factory=list)
    actionable_backlog: list[dict] = Field(default_factory=list)
    stale_leases: list[dict] = Field(default_factory=list)
    repeated_failures: list[dict] = Field(default_factory=list)
    rate_limit_state: dict[str, dict] = Field(default_factory=dict)
    evidence_failures: list[dict] = Field(default_factory=list)
    open_proposals: list[dict] = Field(default_factory=list)
    last_success: dict[str, str | None] = Field(default_factory=dict)
    state_failures: list[dict] = Field(default_factory=list)
    healthy: bool
