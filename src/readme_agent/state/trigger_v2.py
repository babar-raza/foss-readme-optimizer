"""Normalize provider events into immutable TriggerEnvelopeV2 records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from readme_agent import env
from readme_agent.errors import StateBackendError
from readme_agent.state.lifecycle_schema import TriggerEnvelopeV2, TriggerEventTypeV2


def normalize_trigger_envelope(
    org_repo: str,
    *,
    event_type: TriggerEventTypeV2,
    provider_event_id: str | None = None,
    delivery_id: str | None = None,
    workflow_run_id: str | None = None,
    source_revision: str | None = None,
    schedule_window: str | None = None,
    occurred_at: str | None = None,
) -> TriggerEnvelopeV2:
    if event_type == "schedule":
        if not schedule_window:
            raise StateBackendError("schedule trigger is missing its stable schedule window")
        dedup_key = f"schedule:{org_repo}:{schedule_window}"
    elif event_type == "repository_dispatch":
        identity = delivery_id or provider_event_id
        if not identity:
            raise StateBackendError(
                "repository_dispatch trigger is missing delivery/provider event identity"
            )
        dedup_key = f"delivery:{identity}"
    elif event_type in {"workflow_dispatch", "workflow_call"}:
        identity = workflow_run_id or provider_event_id
        if not identity:
            raise StateBackendError(f"{event_type} trigger is missing workflow run identity")
        dedup_key = f"run:{identity}:{org_repo}"
    else:
        identity = provider_event_id or workflow_run_id
        if not identity:
            raise StateBackendError(f"{event_type} trigger is missing provider identity")
        dedup_key = f"operator:{identity}:{org_repo}"
    provider_id = provider_event_id or delivery_id or workflow_run_id or schedule_window
    assert provider_id is not None
    return TriggerEnvelopeV2(
        provider_event_id=provider_id,
        event_type=event_type,
        repository_scope=org_repo,
        delivery_id=delivery_id,
        workflow_run_id=workflow_run_id,
        source_revision=source_revision,
        schedule_window=schedule_window,
        occurred_at=occurred_at or datetime.now(UTC).isoformat(),
        dedup_key=dedup_key,
    )


def normalize_github_trigger(org_repo: str) -> TriggerEnvelopeV2:
    event_name = env.github_event_name()
    if event_name not in {
        "schedule",
        "workflow_dispatch",
        "workflow_call",
        "repository_dispatch",
    }:
        raise StateBackendError(f"unsupported GitHub trigger type {event_name!r}")
    return normalize_trigger_envelope(
        org_repo,
        event_type=cast(TriggerEventTypeV2, event_name),
        provider_event_id=env.trigger_provider_event_id(),
        delivery_id=env.trigger_delivery_id(),
        workflow_run_id=env.github_run_id(),
        source_revision=env.github_sha(),
        schedule_window=env.trigger_schedule_window(),
    )
