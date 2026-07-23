"""Explicit durable-state migrations with fail-closed version handling."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import ValidationError

from readme_agent.errors import StateBackendError
from readme_agent.state.lifecycle_schema import (
    CheckpointV1,
    TriggerEnvelopeV2,
    TriggerLifecycleV2,
)
from readme_agent.state.schema import RunStateV1, RunStateV2, TriggerRecordV1

CURRENT_RUN_STATE_SCHEMA_VERSION = 2


def _legacy_envelope(trigger: TriggerRecordV1) -> TriggerEnvelopeV2:
    dedup_key = trigger.dedup_key()
    provider_event_id = (
        trigger.manual_request_id
        or trigger.delivery_id
        or trigger.workflow_run_id
        or hashlib.sha256(dedup_key.encode("utf-8")).hexdigest()
    )
    return TriggerEnvelopeV2(
        provider_event_id=provider_event_id,
        event_type=trigger.event_type,
        repository_scope=trigger.org_repo,
        delivery_id=trigger.delivery_id,
        workflow_run_id=trigger.workflow_run_id,
        source_revision=trigger.source_revision,
        schedule_window=trigger.schedule_window,
        occurred_at=trigger.accepted_at,
        dedup_key=dedup_key,
    )


def _migrate_v1(raw: dict[str, Any]) -> RunStateV2:
    legacy = RunStateV1.model_validate(raw)
    lifecycles: dict[str, TriggerLifecycleV2] = {}
    checkpoints: dict[str, CheckpointV1] = {}
    for key, trigger in legacy.trigger_records.items():
        envelope = _legacy_envelope(trigger)
        checkpoint_id = hashlib.sha256(f"{key}:legacy:trigger_accepted".encode()).hexdigest()
        lifecycles[key] = TriggerLifecycleV2(
            envelope=envelope,
            status=trigger.status,
            accepted_at=trigger.accepted_at,
            updated_at=trigger.accepted_at,
            last_checkpoint_id=checkpoint_id,
        )
        checkpoints[checkpoint_id] = CheckpointV1(
            checkpoint_id=checkpoint_id,
            trigger_dedup_key=key,
            run_id=trigger.workflow_run_id or f"legacy-{checkpoint_id[:12]}",
            repository=trigger.org_repo,
            stage="trigger_accepted",
            input_hash=hashlib.sha256(envelope.model_dump_json().encode("utf-8")).hexdigest(),
            started_at=trigger.accepted_at,
            completed_at=trigger.accepted_at,
            detail="migrated from TriggerRecordV1",
        )
    return RunStateV2.model_validate(
        {
            **legacy.model_dump(mode="json"),
            "schema_version": CURRENT_RUN_STATE_SCHEMA_VERSION,
            "trigger_lifecycles": lifecycles,
            "checkpoints": checkpoints,
        }
    )


def load_run_state_json(payload: str) -> RunStateV2:
    """Parse and migrate a serialized state blob, rejecting unknown versions."""

    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise StateBackendError(f"durable state is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise StateBackendError("durable state must be a JSON object")
    version = raw.get("schema_version", 1)
    if version == 1:
        try:
            return _migrate_v1(raw)
        except ValidationError as exc:
            raise StateBackendError(f"RunStateV1 migration failed: {exc}") from exc
    if version != CURRENT_RUN_STATE_SCHEMA_VERSION:
        raise StateBackendError(
            f"unsupported durable-state schema version {version!r}; "
            f"this runner supports up to {CURRENT_RUN_STATE_SCHEMA_VERSION}"
        )
    try:
        return RunStateV2.model_validate(raw)
    except ValidationError as exc:
        raise StateBackendError(f"RunStateV2 validation failed: {exc}") from exc


def ensure_run_state_v2(state: RunStateV1 | RunStateV2) -> RunStateV2:
    if isinstance(state, RunStateV2):
        return state
    return _migrate_v1(state.model_dump(mode="json"))
