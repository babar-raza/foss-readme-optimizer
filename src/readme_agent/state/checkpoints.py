"""Persist immutable lifecycle checkpoints."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import StateBackend
from readme_agent.state.cas import save_state_patch
from readme_agent.state.lifecycle_schema import (
    CheckpointStageV1,
    CheckpointV1,
    FailureClassificationV1,
    TriggerEnvelopeV2,
)
from readme_agent.state.schema import RunStateV2

MAX_CHECKPOINTS_PER_REPO = 1_000


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_checkpoint(
    backend: StateBackend,
    envelope: TriggerEnvelopeV2,
    *,
    run_id: str,
    stage: CheckpointStageV1,
    task_id: str | None = None,
    action: str | None = None,
    attempt: int = 1,
    inputs: Any = None,
    outputs: Any = None,
    failure_classification: FailureClassificationV1 | None = None,
    detail: str | None = None,
) -> CheckpointV1:
    input_hash = canonical_hash(inputs) if inputs is not None else None
    output_hash = canonical_hash(outputs) if outputs is not None else None
    identity = {
        "trigger": envelope.dedup_key,
        "run": run_id,
        "stage": stage,
        "task": task_id,
        "action": action,
        "attempt": attempt,
        "input_hash": input_hash,
    }
    checkpoint_id = canonical_hash(identity)
    checkpoint = CheckpointV1(
        checkpoint_id=checkpoint_id,
        trigger_dedup_key=envelope.dedup_key,
        run_id=run_id,
        repository=envelope.repository_scope,
        stage=stage,
        task_id=task_id,
        action=action,
        attempt=attempt,
        input_hash=input_hash,
        output_hash=output_hash,
        failure_classification=failure_classification,
        detail=detail,
    )

    def semantic_fields(value: CheckpointV1) -> dict[str, Any]:
        return value.model_dump(exclude={"started_at", "completed_at"})

    def patch(state: RunStateV2) -> RunStateV2:
        lifecycle = state.trigger_lifecycles.get(envelope.dedup_key)
        if lifecycle is None:
            raise StateBackendError(f"cannot checkpoint unknown trigger {envelope.dedup_key!r}")
        checkpoints = dict(state.checkpoints)
        existing = checkpoints.get(checkpoint_id)
        if existing is not None:
            if semantic_fields(existing) != semantic_fields(checkpoint):
                raise StateBackendError(f"checkpoint identity collision for {checkpoint_id}")
            return state
        checkpoints[checkpoint_id] = checkpoint
        if len(checkpoints) > MAX_CHECKPOINTS_PER_REPO:
            oldest = min(checkpoints, key=lambda key: checkpoints[key].completed_at)
            del checkpoints[oldest]
        records = dict(state.trigger_lifecycles)
        records[envelope.dedup_key] = lifecycle.model_copy(
            update={
                "updated_at": checkpoint.completed_at,
                "last_checkpoint_id": checkpoint_id,
            }
        )
        return state.model_copy(update={"checkpoints": checkpoints, "trigger_lifecycles": records})

    saved = save_state_patch(backend, envelope.repository_scope, patch)
    return saved.checkpoints[checkpoint_id]
