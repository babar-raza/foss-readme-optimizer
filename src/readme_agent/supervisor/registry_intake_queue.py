"""Settle discovery changes through the existing durable intake lifecycle."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.registry.models import ProductEntry
from readme_agent.registry.revision import RegistryRevisionV1
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle import accept_trigger, transition_trigger
from readme_agent.state.trigger_v2 import normalize_trigger_envelope
from readme_agent.supervisor.intake import run_readonly_intake_preflight

_SETTLED_OUTCOMES = {"READY_FAST_PATH", "READY_FULL_PIPELINE", "NOT_APPLICABLE"}


class RegistryIntakeQueueItemV1(BaseModel):
    """Outcome of delivering one discovery observation to read-only intake."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str
    trigger_dedup_key: str
    observation_revision: str
    trigger_executed: bool
    intake_executed: bool
    outcome: str
    settled: bool


class RegistryIntakeQueueResultV1(BaseModel):
    """Complete queue settlement result for one registry revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    revision_id: str
    items: list[RegistryIntakeQueueItemV1] = Field(default_factory=list)
    pending_intake: list[str] = Field(default_factory=list)


def settle_registry_intake_queue(
    revision: RegistryRevisionV1,
    entries: list[ProductEntry],
    backend: StateBackend,
) -> RegistryIntakeQueueResultV1:
    """Deliver each pending observation once and resume its source-bound intake."""

    by_name = {entry.org_repo: entry for entry in entries}
    changes = {change.org_repo: change for change in revision.observation_changes}
    items: list[RegistryIntakeQueueItemV1] = []
    pending: list[str] = []
    for org_repo in revision.pending_intake:
        entry = by_name.get(org_repo)
        change = changes.get(org_repo)
        if entry is None or entry.provider_identity is None:
            pending.append(org_repo)
            continue
        observation_revision = (
            change.observation_revision
            if change is not None
            else revision.observation_revisions.get(
                str(entry.provider_identity.repository_id),
                "0" * 64,
            )
        )
        delivery_id = f"registry:{entry.provider_identity.repository_id}:{observation_revision}"
        envelope = normalize_trigger_envelope(
            org_repo,
            event_type="repository_dispatch",
            provider_event_id=delivery_id,
            delivery_id=delivery_id,
            source_revision=observation_revision,
            occurred_at=revision.captured_at,
        )
        acceptance = accept_trigger(backend, envelope)
        trigger_executed = acceptance.should_execute
        try:
            if trigger_executed:
                transition_trigger(backend, org_repo, envelope.dedup_key, "processing")
            intake = run_readonly_intake_preflight(entry, backend)
            if trigger_executed:
                transition_trigger(backend, org_repo, envelope.dedup_key, "completed")
        except Exception as exc:
            if trigger_executed:
                transition_trigger(
                    backend,
                    org_repo,
                    envelope.dedup_key,
                    "retryable",
                    failure_classification="transient",
                    failure_detail=f"registry_intake_queue:{type(exc).__name__}",
                )
            pending.append(org_repo)
            continue
        settled = intake.binding.outcome in _SETTLED_OUTCOMES
        if not settled:
            pending.append(org_repo)
        items.append(
            RegistryIntakeQueueItemV1(
                org_repo=org_repo,
                trigger_dedup_key=envelope.dedup_key,
                observation_revision=observation_revision,
                trigger_executed=trigger_executed,
                intake_executed=intake.executed,
                outcome=intake.binding.outcome,
                settled=settled,
            )
        )
    return RegistryIntakeQueueResultV1(
        revision_id=revision.revision_id,
        items=items,
        pending_intake=sorted(set(pending)),
    )
