"""Recover stale unfinished lifecycle work."""

from __future__ import annotations

from datetime import UTC, datetime

from readme_agent.state.backend import StateBackend
from readme_agent.state.cas import save_state_patch
from readme_agent.state.lifecycle_schema import RecoveryCandidateV1, TriggerStatusV2
from readme_agent.state.schema import RunStateV2

DEFAULT_PROCESSING_LEASE_SECONDS = 900


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def recovery_sweep(
    backend: StateBackend,
    repositories: list[str],
    *,
    now: datetime | None = None,
    stale_after_seconds: int = DEFAULT_PROCESSING_LEASE_SECONDS,
) -> list[RecoveryCandidateV1]:
    """Mark stale accepted/processing/retryable work visibly retryable."""

    observed_at = now or datetime.now(UTC)
    candidates: list[RecoveryCandidateV1] = []
    for org_repo in repositories:
        state = backend.load(org_repo)
        if state is None:
            continue
        eligible: dict[str, tuple[TriggerStatusV2, int]] = {}
        for key, lifecycle in state.trigger_lifecycles.items():
            if lifecycle.status not in {"accepted", "processing", "retryable"}:
                continue
            updated_at = _parse_time(lifecycle.updated_at)
            lease_expired = (
                lifecycle.lease_expires_at is not None
                and _parse_time(lifecycle.lease_expires_at) <= observed_at
            )
            stale = (observed_at - updated_at).total_seconds() >= stale_after_seconds
            if not lease_expired and not stale:
                continue
            eligible[key] = (lifecycle.status, lifecycle.recovery_count)

        if not eligible:
            continue

        def patch(
            current: RunStateV2,
            trigger_keys: tuple[str, ...] = tuple(eligible),
        ) -> RunStateV2:
            records = dict(current.trigger_lifecycles)
            changed = False
            for trigger_key in trigger_keys:
                latest = records.get(trigger_key)
                if latest is None:
                    continue
                if latest.status not in {"accepted", "processing", "retryable"}:
                    continue
                updated_at = _parse_time(latest.updated_at)
                lease_expired = (
                    latest.lease_expires_at is not None
                    and _parse_time(latest.lease_expires_at) <= observed_at
                )
                stale = (observed_at - updated_at).total_seconds() >= stale_after_seconds
                if not lease_expired and not stale:
                    continue
                records[trigger_key] = latest.model_copy(
                    update={
                        "status": "retryable",
                        "updated_at": observed_at.isoformat(),
                        "lease_expires_at": None,
                        "failure_classification": "transient",
                        "failure_detail": "recovery_sweep_stale_or_expired",
                        "recovery_count": latest.recovery_count + 1,
                    }
                )
                changed = True
            if not changed:
                return current
            return current.model_copy(update={"trigger_lifecycles": records})

        saved = save_state_patch(backend, org_repo, patch)
        for key, (prior_status, prior_recovery_count) in eligible.items():
            recovered = saved.trigger_lifecycles[key]
            if recovered.recovery_count <= prior_recovery_count:
                continue
            candidates.append(
                RecoveryCandidateV1(
                    repository=org_repo,
                    trigger_dedup_key=key,
                    prior_status=prior_status,
                    last_checkpoint_id=recovered.last_checkpoint_id,
                    recovery_count=recovered.recovery_count,
                    reason="stale_or_expired_processing_lease",
                )
            )
    return candidates
