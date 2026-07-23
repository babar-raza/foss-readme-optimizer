"""Coordinate trigger acceptance, transitions, and active lifecycle context."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import StateBackend, safe_release_lock
from readme_agent.state.cas import load_required_state, save_state_patch
from readme_agent.state.checkpoints import record_checkpoint
from readme_agent.state.lifecycle_schema import (
    CheckpointStageV1,
    CheckpointV1,
    FailureClassificationV1,
    TriggerEnvelopeV2,
    TriggerLifecycleV2,
    TriggerStatusV2,
)
from readme_agent.state.schema import RunStateV2

DEFAULT_PROCESSING_LEASE_SECONDS = 900
_TERMINAL_STATUSES: set[TriggerStatusV2] = {
    "blocked",
    "failed",
    "completed",
    "deduplicated",
}
_ALLOWED_TRANSITIONS: dict[TriggerStatusV2, set[TriggerStatusV2]] = {
    "accepted": {"processing", "blocked", "failed", "deduplicated"},
    "processing": {"retryable", "blocked", "failed", "completed"},
    "retryable": {"processing", "blocked", "failed"},
    "blocked": set(),
    "failed": set(),
    "completed": {"deduplicated"},
    "deduplicated": set(),
}
_ACTIVE_RECORDER: ContextVar[LifecycleRecorder | None] = ContextVar(
    "readme_agent_lifecycle_recorder",
    default=None,
)


@dataclass(frozen=True)
class TriggerAcceptance:
    lifecycle: TriggerLifecycleV2
    should_execute: bool
    resumed: bool = False


def accept_trigger(
    backend: StateBackend,
    envelope: TriggerEnvelopeV2,
    *,
    max_retries: int = 5,
) -> TriggerAcceptance:
    """Accept once; unfinished duplicates resume instead of being suppressed."""

    org_repo = envelope.repository_scope
    lock = backend.acquire_lock(org_repo)
    if lock is None:
        raise StateBackendError(f"could not acquire lifecycle lock for {org_repo!r}")
    try:
        current = backend.load(org_repo)
        if current is not None:
            existing = current.trigger_lifecycles.get(envelope.dedup_key)
            if existing is not None:
                if existing.status in {"accepted", "processing", "retryable"}:
                    return TriggerAcceptance(existing, should_execute=True, resumed=True)
                duplicate = existing.model_copy(
                    update={"status": "deduplicated", "updated_at": datetime.now(UTC).isoformat()}
                )
                return TriggerAcceptance(duplicate, should_execute=False)

        lifecycle = TriggerLifecycleV2(envelope=envelope)

        def patch(state: RunStateV2) -> RunStateV2:
            records = dict(state.trigger_lifecycles)
            prior = records.get(envelope.dedup_key)
            if prior is not None:
                return state
            records[envelope.dedup_key] = lifecycle
            return state.model_copy(update={"trigger_lifecycles": records})

        saved = save_state_patch(backend, org_repo, patch, max_retries=max_retries)
        accepted = saved.trigger_lifecycles[envelope.dedup_key]
        return TriggerAcceptance(accepted, should_execute=True)
    finally:
        safe_release_lock(backend.release_lock, lock, label="lifecycle-lock")


def transition_trigger(
    backend: StateBackend,
    org_repo: str,
    dedup_key: str,
    status: TriggerStatusV2,
    *,
    failure_classification: FailureClassificationV1 | None = None,
    failure_detail: str | None = None,
    lease_seconds: int = DEFAULT_PROCESSING_LEASE_SECONDS,
) -> TriggerLifecycleV2:
    now = datetime.now(UTC)

    def patch(state: RunStateV2) -> RunStateV2:
        current = state.trigger_lifecycles.get(dedup_key)
        if current is None:
            raise StateBackendError(f"unknown trigger {dedup_key!r} for {org_repo!r}")
        if status != current.status and status not in _ALLOWED_TRANSITIONS[current.status]:
            raise StateBackendError(
                f"invalid trigger transition {current.status!r} -> {status!r} for {dedup_key!r}"
            )
        records = dict(state.trigger_lifecycles)
        records[dedup_key] = current.model_copy(
            update={
                "status": status,
                "updated_at": now.isoformat(),
                "lease_expires_at": (
                    (now + timedelta(seconds=lease_seconds)).isoformat()
                    if status == "processing"
                    else None
                ),
                "failure_classification": failure_classification,
                "failure_detail": failure_detail,
            }
        )
        return state.model_copy(update={"trigger_lifecycles": records})

    saved = save_state_patch(backend, org_repo, patch)
    return saved.trigger_lifecycles[dedup_key]


@dataclass
class LifecycleRecorder:
    backend: StateBackend
    envelope: TriggerEnvelopeV2
    run_id: str
    attempt: int = 1

    def checkpoint(self, stage: CheckpointStageV1, **kwargs: Any) -> CheckpointV1:
        return record_checkpoint(
            self.backend,
            self.envelope,
            run_id=self.run_id,
            stage=stage,
            attempt=self.attempt,
            **kwargs,
        )

    def start(self) -> None:
        transition_trigger(
            self.backend,
            self.envelope.repository_scope,
            self.envelope.dedup_key,
            "processing",
        )
        self.checkpoint("run_started", inputs={"repository": self.envelope.repository_scope})

    def finish(
        self,
        status: TriggerStatusV2,
        *,
        detail: str | None = None,
        failure_classification: FailureClassificationV1 | None = None,
    ) -> None:
        self.checkpoint_final_acceptance(
            status,
            detail=detail,
            failure_classification=failure_classification,
        )
        self.transition(
            status,
            detail=detail,
            failure_classification=failure_classification,
        )

    def checkpoint_final_acceptance(
        self,
        status: TriggerStatusV2,
        *,
        detail: str | None = None,
        failure_classification: FailureClassificationV1 | None = None,
    ) -> CheckpointV1:
        """Persist the intended terminal result before evidence finalization."""

        return self.checkpoint(
            "final_acceptance",
            outputs={"status": status, "detail": detail},
            failure_classification=failure_classification,
        )

    def transition(
        self,
        status: TriggerStatusV2,
        *,
        detail: str | None = None,
        failure_classification: FailureClassificationV1 | None = None,
    ) -> None:
        """Persist lifecycle status after all preceding acceptance gates pass."""

        transition_trigger(
            self.backend,
            self.envelope.repository_scope,
            self.envelope.dedup_key,
            status,
            failure_classification=failure_classification,
            failure_detail=detail,
        )

    def checkpoints(self) -> list[CheckpointV1]:
        state = load_required_state(self.backend, self.envelope.repository_scope)
        return sorted(
            (
                checkpoint
                for checkpoint in state.checkpoints.values()
                if checkpoint.trigger_dedup_key == self.envelope.dedup_key
            ),
            key=lambda checkpoint: checkpoint.completed_at,
        )


def current_lifecycle_recorder() -> LifecycleRecorder | None:
    return _ACTIVE_RECORDER.get()


@contextmanager
def activate_lifecycle(recorder: LifecycleRecorder | None):
    token = _ACTIVE_RECORDER.set(recorder)
    try:
        yield
    finally:
        _ACTIVE_RECORDER.reset(token)
