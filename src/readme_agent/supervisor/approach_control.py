"""Enforce bounded attempts, first-principles replanning, and command authority."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

from readme_agent.state.agile_execution_schema import (
    ApproachAdmissionDecisionV1,
    ApproachAttemptV1,
    ApproachControlStateV1,
    FirstPrinciplesReplanV1,
    SafeCommandAuthorityDecisionV1,
    SafeCommandAuthorityRequestV1,
)
from readme_agent.supervisor.mission_schema import TaskCardV1

DEFAULT_NARROWING_LIMIT = timedelta(minutes=15)


def task_approach_fingerprint(task: TaskCardV1) -> str:
    """Stable default fingerprint for the task's causal execution mechanism."""

    payload = {
        "task_id": task.task_id,
        "lane": task.lane,
        "objective": task.objective,
        "dependencies": task.dependencies,
        "core_contribution": task.core_contribution.model_dump(mode="json"),
        "execution_kind": task.execution_kind,
        "execution_focus": (
            task.execution_focus.model_dump(mode="json") if task.execution_focus else None
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def proposed_fingerprint(state: ApproachControlStateV1, task: TaskCardV1) -> str:
    return state.proposed_fingerprints.get(task.task_id, task_approach_fingerprint(task))


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def decide_approach_admission(
    state: ApproachControlStateV1,
    task: TaskCardV1,
    *,
    now: datetime | None = None,
) -> ApproachAdmissionDecisionV1:
    """Reject a third equivalent attempt or an unnarrowed fifteen-minute continuation."""

    now = now or datetime.now(UTC)
    fingerprint = proposed_fingerprint(state, task)
    matching = [
        attempt
        for attempt in state.attempts
        if attempt.task_id == task.task_id and attempt.fingerprint == fingerprint
    ]
    max_ineffective = (
        task.execution_focus.max_equivalent_ineffective_attempts if task.execution_focus else 2
    )
    narrowing_limit = (
        timedelta(minutes=task.execution_focus.max_minutes_without_narrowing)
        if task.execution_focus
        else DEFAULT_NARROWING_LIMIT
    )
    ineffective = sum(attempt.outcome == "ineffective" for attempt in matching)
    latest = matching[-1] if matching else None
    timed_out = False
    if latest is not None and latest.outcome == "in_progress":
        watermark = latest.last_material_narrowing_at or latest.started_at
        timed_out = now - _parse_time(watermark) >= narrowing_limit
    requires_replan = ineffective >= max_ineffective or timed_out
    reason = "approach admitted"
    if ineffective >= max_ineffective:
        reason = (
            f"{max_ineffective} equivalent ineffective attempts require a first-principles replan"
        )
    elif timed_out:
        minutes = int(narrowing_limit.total_seconds() // 60)
        reason = f"{minutes} minutes without material narrowing require a first-principles replan"
    return ApproachAdmissionDecisionV1(
        task_id=task.task_id,
        admitted=not requires_replan,
        fingerprint=fingerprint,
        reason=reason,
        equivalent_ineffective_attempts=ineffective,
        requires_first_principles_replan=requires_replan,
    )


def start_approach_attempt(
    state: ApproachControlStateV1,
    task: TaskCardV1,
    *,
    now: datetime | None = None,
) -> ApproachControlStateV1:
    """Append one durable attempt unless this exact attempt is already active."""

    now = now or datetime.now(UTC)
    decision = decide_approach_admission(state, task, now=now)
    if not decision.admitted:
        raise ValueError(decision.reason)
    if state.attempts:
        latest = state.attempts[-1]
        if (
            latest.task_id == task.task_id
            and latest.fingerprint == decision.fingerprint
            and latest.outcome == "in_progress"
        ):
            return state
    attempt = ApproachAttemptV1(
        task_id=task.task_id,
        fingerprint=decision.fingerprint,
        started_at=now.isoformat(),
    )
    return state.model_copy(update={"attempts": [*state.attempts, attempt]})


def finish_latest_attempt(
    state: ApproachControlStateV1,
    task_id: str,
    *,
    effective: bool,
    evidence_refs: list[str],
    narrowed_at: str | None = None,
) -> ApproachControlStateV1:
    """Close the latest in-progress attempt without rewriting earlier attempts."""

    attempts = list(state.attempts)
    index = next(
        (
            position
            for position in range(len(attempts) - 1, -1, -1)
            if attempts[position].task_id == task_id and attempts[position].outcome == "in_progress"
        ),
        None,
    )
    if index is None:
        return state
    attempts[index] = attempts[index].model_copy(
        update={
            "outcome": "effective" if effective else "ineffective",
            "evidence_refs": evidence_refs,
            "last_material_narrowing_at": narrowed_at,
        }
    )
    return state.model_copy(update={"attempts": attempts})


def record_material_narrowing(
    state: ApproachControlStateV1,
    task_id: str,
    *,
    evidence_refs: list[str],
    narrowed_at: str | None = None,
) -> ApproachControlStateV1:
    """Refresh the anti-stall watermark for the current append-only attempt."""

    attempts = list(state.attempts)
    index = next(
        (
            position
            for position in range(len(attempts) - 1, -1, -1)
            if attempts[position].task_id == task_id and attempts[position].outcome == "in_progress"
        ),
        None,
    )
    if index is None:
        raise ValueError(f"task {task_id!r} has no in-progress approach attempt")
    timestamp = narrowed_at or datetime.now(UTC).isoformat()
    attempts[index] = attempts[index].model_copy(
        update={
            "last_material_narrowing_at": timestamp,
            "evidence_refs": list(dict.fromkeys([*attempts[index].evidence_refs, *evidence_refs])),
        }
    )
    return state.model_copy(update={"attempts": attempts})


def validate_approach_closeout(
    state: ApproachControlStateV1,
    task: TaskCardV1,
    *,
    now: datetime | None = None,
) -> None:
    """Require one effective admitted attempt for the current approach fingerprint."""

    decision = decide_approach_admission(state, task, now=now)
    if not decision.admitted:
        raise ValueError(decision.reason)
    matching = [
        attempt
        for attempt in state.attempts
        if attempt.task_id == task.task_id
        and attempt.fingerprint == decision.fingerprint
        and attempt.outcome == "effective"
    ]
    if not matching:
        raise ValueError("task closeout requires an effective durable approach attempt")


def apply_first_principles_replan(
    state: ApproachControlStateV1,
    replan: FirstPrinciplesReplanV1,
) -> ApproachControlStateV1:
    """Install a materially changed fingerprint after a structured causal review."""

    current = state.proposed_fingerprints.get(replan.task_id)
    if current is None:
        matching = [item for item in state.attempts if item.task_id == replan.task_id]
        current = matching[-1].fingerprint if matching else None
    if current != replan.prior_fingerprint:
        raise ValueError("replan prior fingerprint does not match the durable current approach")
    proposed = {**state.proposed_fingerprints, replan.task_id: replan.new_fingerprint}
    return state.model_copy(
        update={
            "replans": [*state.replans, replan],
            "proposed_fingerprints": proposed,
        }
    )


def decide_safe_command_authority(
    request: SafeCommandAuthorityRequestV1,
) -> SafeCommandAuthorityDecisionV1:
    """Auto-proceed on clear local work; reserve real authority boundaries for humans."""

    if not request.plan_bound:
        return SafeCommandAuthorityDecisionV1(
            disposition="REJECT_NOT_PLAN_BOUND",
            reason="the command is outside the governed task",
        )
    if any(
        (
            request.destructive,
            request.external_effect,
            request.credentials_required,
            request.manual_ui_required,
            not request.local_only,
        )
    ):
        return SafeCommandAuthorityDecisionV1(
            disposition="HUMAN_AUTHORITY_REQUIRED",
            reason="the command crosses an external, destructive, credential, or manual boundary",
        )
    return SafeCommandAuthorityDecisionV1(
        disposition="AUTO_PROCEED",
        reason="clear safe plan-bound local work has standing command authority",
    )
