"""Aggregate durable lifecycle state into a typed portfolio health report."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import HealthReportV1


def build_health_report(
    backend: StateBackend,
    repositories: list[str],
    *,
    now: datetime | None = None,
    expected_schedule_interval: timedelta = timedelta(days=1),
    backlog_sla: timedelta = timedelta(minutes=15),
    repeated_failure_threshold: int = 3,
) -> HealthReportV1:
    observed_at = now or datetime.now(UTC)
    missed: list[dict] = []
    backlog: list[dict] = []
    actionable_backlog: list[dict] = []
    stale_leases: list[dict] = []
    repeated_failures: list[dict] = []
    evidence_failures: list[dict] = []
    open_proposals: list[dict] = []
    state_failures: list[dict] = []
    last_success: dict[str, str | None] = {}

    for org_repo in repositories:
        try:
            state = backend.load(org_repo)
        except Exception as exc:  # noqa: BLE001 -- health must expose every backend failure
            state_failures.append({"repository": org_repo, "error": str(exc)})
            last_success[org_repo] = None
            continue
        if state is None:
            missed.append({"repository": org_repo, "reason": "no_durable_state"})
            last_success[org_repo] = None
            continue

        completed = [
            lifecycle
            for lifecycle in state.trigger_lifecycles.values()
            if lifecycle.status == "completed"
        ]
        latest_success = max((item.updated_at for item in completed), default=None)
        last_success[org_repo] = latest_success
        if (
            latest_success is None
            or (observed_at - datetime.fromisoformat(latest_success)) > expected_schedule_interval
        ):
            missed.append(
                {
                    "repository": org_repo,
                    "last_success": latest_success,
                    "expected_within_seconds": int(expected_schedule_interval.total_seconds()),
                }
            )

        for key, lifecycle in state.trigger_lifecycles.items():
            if lifecycle.status in {"accepted", "processing", "retryable"}:
                age_seconds = max(
                    0,
                    int(
                        (observed_at - datetime.fromisoformat(lifecycle.updated_at)).total_seconds()
                    ),
                )
                actionable = lifecycle.status == "retryable" or age_seconds >= int(
                    backlog_sla.total_seconds()
                )
                backlog_item = {
                    "repository": org_repo,
                    "dedup_key": key,
                    "status": lifecycle.status,
                    "updated_at": lifecycle.updated_at,
                    "age_seconds": age_seconds,
                    "actionable": actionable,
                    "reason": (
                        "retryable_work_requires_recovery"
                        if lifecycle.status == "retryable"
                        else ("backlog_sla_exceeded" if actionable else "bounded_in_flight_work")
                    ),
                }
                backlog.append(backlog_item)
                if actionable:
                    actionable_backlog.append(backlog_item)
            if (
                lifecycle.lease_expires_at
                and datetime.fromisoformat(lifecycle.lease_expires_at) <= observed_at
            ):
                stale_leases.append(
                    {
                        "repository": org_repo,
                        "dedup_key": key,
                        "lease_expires_at": lifecycle.lease_expires_at,
                    }
                )
            if lifecycle.recovery_count >= repeated_failure_threshold:
                repeated_failures.append(
                    {
                        "repository": org_repo,
                        "dedup_key": key,
                        "recovery_count": lifecycle.recovery_count,
                        "failure_detail": lifecycle.failure_detail,
                    }
                )

        for domain, proposal in state.open_proposals.items():
            if proposal.state == "open":
                open_proposals.append(
                    {
                        "repository": org_repo,
                        "domain": domain,
                        "pr_url": proposal.pr_url,
                        "opened_at": proposal.opened_at,
                    }
                )

    healthy = not any(
        (
            missed,
            actionable_backlog,
            stale_leases,
            repeated_failures,
            evidence_failures,
            state_failures,
        )
    )
    return HealthReportV1(
        repositories_checked=len(repositories),
        missed_schedule_windows=missed,
        backlog=backlog,
        actionable_backlog=actionable_backlog,
        stale_leases=stale_leases,
        repeated_failures=repeated_failures,
        evidence_failures=evidence_failures,
        open_proposals=open_proposals,
        last_success=last_success,
        state_failures=state_failures,
        healthy=healthy,
    )
