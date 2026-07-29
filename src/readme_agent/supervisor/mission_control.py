"""Load, validate, claim, transition, and evaluate central mission taskcards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from readme_agent.errors import ConfigError, StateBackendError
from readme_agent.state.backend import StateBackend
from readme_agent.state.mission_goal_schema import (
    MissionGoalTransitionV1,
    MissionLifecycleScoreboardV1,
    MissionNextTaskV1,
    StageGoalId,
)
from readme_agent.state.schema import (
    MissionExecutionStateV1,
    MissionTaskStatus,
    MissionTransitionV1,
    RunStateV1,
)
from readme_agent.supervisor.mission_goal_guard import (
    derive_lifecycle_scoreboard,
    validate_task_contribution_evidence,
)
from readme_agent.supervisor.mission_schema import MissionTaskGraphV1, TaskCardV1

_TERMINAL_SUCCESS = {"CLOSED"}
_TERMINAL_EXCEPTION = {
    "BLOCKED",
    "BLOCKED_EXTERNAL",
    "REROUTED",
    "DEFERRED_WITH_REASON",
}
_TERMINAL = _TERMINAL_SUCCESS | _TERMINAL_EXCEPTION
# Rerouting delegates work; it never proves completion. A dependency unlocks
# only after the delegated parent has been reopened and closed from aggregate
# child evidence.
_DEPENDENCY_SATISFIED = _TERMINAL_SUCCESS
_CLAIM_LEASE = timedelta(minutes=30)
_TRANSITIONS: dict[MissionTaskStatus, set[MissionTaskStatus]] = {
    "TODO": {"READY", "BLOCKED", "BLOCKED_EXTERNAL", "DEFERRED_WITH_REASON"},
    "READY": {"IN_PROGRESS", "BLOCKED", "BLOCKED_EXTERNAL", "DEFERRED_WITH_REASON"},
    "IN_PROGRESS": {"IMPLEMENTED", "BLOCKED", "BLOCKED_EXTERNAL", "REROUTED", "REGRESSED"},
    "IMPLEMENTED": {"VERIFIED", "REOPENED", "REGRESSED"},
    "VERIFIED": {"SCORED", "REOPENED", "REGRESSED"},
    "SCORED": {"CLOSED", "REOPENED", "REGRESSED"},
    "CLOSED": {"REOPENED", "REGRESSED"},
    "BLOCKED": {"READY", "REROUTED", "BLOCKED_EXTERNAL"},
    "BLOCKED_EXTERNAL": {"REOPENED"},
    "REROUTED": {"READY", "DEFERRED_WITH_REASON"},
    "DEFERRED_WITH_REASON": {"REOPENED"},
    "REOPENED": {"READY", "BLOCKED", "BLOCKED_EXTERNAL"},
    "REGRESSED": {"READY", "BLOCKED", "BLOCKED_EXTERNAL"},
}
_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


@dataclass(frozen=True)
class MissionEvaluation:
    mission_id: str
    active_task: TaskCardV1 | None
    eligible_tasks: list[TaskCardV1]
    unresolved_task_ids: list[str]
    blocked_external_task_ids: list[str]
    lifecycle_scoreboard: MissionLifecycleScoreboardV1 | None
    next_task: MissionNextTaskV1 | None
    active_goal_id: StageGoalId | None
    concurrent_goal_ids: list[StageGoalId]
    capacity_allocation: dict[str, int]
    core_goal_active: bool
    mission_complete: bool


def mission_state_key(mission_id: str) -> str:
    """Dedicated namespace accepted by the existing per-key Git-ref backend."""
    return f"mission/{mission_id}"


def _initial_state(graph: MissionTaskGraphV1, graph_sha256: str) -> MissionExecutionStateV1:
    statuses = {task.task_id: task.status for task in graph.taskcards}
    active = [task.task_id for task in graph.taskcards if task.status == "IN_PROGRESS"]
    if len(active) > 1:
        raise ConfigError(f"mission graph has multiple IN_PROGRESS tasks: {active}")
    now = datetime.now(UTC)
    return MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_sha256,
        task_statuses=statuses,
        active_task_id=active[0] if active else None,
        claim_id=uuid4().hex if active else None,
        claimed_by=graph.taskcards[0].owner if active else None,
        claimed_at=now.isoformat() if active else None,
        claim_expires_at=(now + _CLAIM_LEASE).isoformat() if active else None,
    )


def has_graph_drift(state: MissionExecutionStateV1, graph_sha256: str) -> bool:
    """Whether read-only status is stale against the graph loaded this invocation."""
    return state.graph_sha256 != graph_sha256


def _claim_expired(state: MissionExecutionStateV1, now: datetime) -> bool:
    """Treat malformed or lease-less active claims as recoverable, never permanent."""
    if state.active_task_id is None:
        return False
    expiry = state.claim_expires_at
    if expiry is None:
        if state.claimed_at is None:
            return True
        expiry = state.claimed_at
        try:
            expiry_at = datetime.fromisoformat(expiry) + _CLAIM_LEASE
        except ValueError:
            return True
    else:
        try:
            expiry_at = datetime.fromisoformat(expiry)
        except ValueError:
            return True
    if expiry_at.tzinfo is None:
        expiry_at = expiry_at.replace(tzinfo=UTC)
    return expiry_at <= now


def _recover_expired_claim(
    state: MissionExecutionStateV1, now: datetime
) -> MissionExecutionStateV1:
    """Release an expired task claim through an append-only recovery transition."""
    task_id = state.active_task_id
    if task_id is None or not _claim_expired(state, now):
        return state
    statuses = dict(state.task_statuses)
    prior = statuses[task_id]
    if prior != "IN_PROGRESS":
        raise StateBackendError(
            f"active mission task {task_id!r} has non-active status {prior!r} during recovery"
        )
    statuses[task_id] = "REGRESSED"
    transition = MissionTransitionV1(
        task_id=task_id,
        from_status="IN_PROGRESS",
        to_status="REGRESSED",
        observed_by="mission-claim-recovery",
        reason="claim lease expired before a terminal verification state",
    )
    return state.model_copy(
        update={
            "task_statuses": statuses,
            "active_task_id": None,
            "claim_id": None,
            "claimed_by": None,
            "claimed_at": None,
            "claim_expires_at": None,
            "transition_history": [*state.transition_history, transition],
            "last_evaluated_at": now.isoformat(),
        }
    )


def _load_or_initialize(
    backend: StateBackend, graph: MissionTaskGraphV1, graph_sha256: str
) -> tuple[RunStateV1, int | None]:
    key = mission_state_key(graph.mission_authority.mission_id)
    record = backend.load(key)
    if record is None:
        return (
            RunStateV1(
                org_repo=key,
                mission_execution=_initial_state(graph, graph_sha256),
            ),
            None,
        )
    if record.mission_execution is None:
        raise StateBackendError(f"state key {key!r} exists without mission_execution")
    state = record.mission_execution
    if state.mission_id != graph.mission_authority.mission_id:
        raise StateBackendError(
            f"state mission {state.mission_id!r} does not match graph "
            f"{graph.mission_authority.mission_id!r}"
        )

    graph_ids = {task.task_id for task in graph.taskcards}
    unknown = set(state.task_statuses) - graph_ids
    if unknown:
        raise StateBackendError(
            f"durable mission state contains orphan task IDs: {sorted(unknown)}"
        )
    merged = dict(state.task_statuses)
    for task in graph.taskcards:
        merged.setdefault(task.task_id, task.status)
    reconciled = state.model_copy(
        update={
            "graph_sha256": graph_sha256,
            "task_statuses": merged,
            "last_evaluated_at": datetime.now(UTC).isoformat(),
        }
    )
    return record.model_copy(update={"mission_execution": reconciled}), record.state_version


def _dependency_ready_tasks(
    graph: MissionTaskGraphV1, state: MissionExecutionStateV1
) -> list[TaskCardV1]:
    by_id = {task.task_id: task for task in graph.taskcards}

    def status_for(task_id: str) -> MissionTaskStatus:
        task = by_id[task_id]
        return state.task_statuses.get(task_id, task.status)

    ready: list[TaskCardV1] = []
    for task in graph.taskcards:
        status = status_for(task.task_id)
        if status not in {"TODO", "READY", "REOPENED", "REGRESSED"}:
            continue
        if all(status_for(dependency) in _DEPENDENCY_SATISFIED for dependency in task.dependencies):
            ready.append(by_id[task.task_id])
    return ready


def _derive_goal_selection(
    graph: MissionTaskGraphV1,
    state: MissionExecutionStateV1,
) -> tuple[StageGoalId | None, list[StageGoalId], dict[str, int]]:
    """Derive primary/concurrent goals from task truth, never narrative selection."""

    goals = sorted(graph.mission_authority.stage_goal_catalog, key=lambda goal: goal.order)
    tasks_by_goal = {
        goal.goal_id: [task for task in graph.taskcards if task.stage_goal_id == goal.goal_id]
        for goal in goals
    }

    def status_for(task: TaskCardV1) -> MissionTaskStatus:
        return state.task_statuses.get(task.task_id, task.status)

    incomplete = [
        goal
        for goal in goals
        if any(status_for(task) != "CLOSED" for task in tasks_by_goal[goal.goal_id])
    ]
    primary = incomplete[0] if incomplete else None
    if primary is None:
        return None, [], {}
    ready = _dependency_ready_tasks(graph, state)
    concurrent = [
        goal.goal_id
        for goal in incomplete[1:]
        if goal.concurrent_when_trusted_primary
        and any(
            task.stage_goal_id == goal.goal_id
            and task.concurrency_class == "read_only_assurance_isolated"
            for task in ready
        )
        and primary.goal_id
        in {
            "GOAL-T0-TRUSTED-QUALIFICATION",
            "GOAL-T1-TRUSTED-PORTFOLIO",
            "GOAL-T2-WORKFLOW-STAGING",
            "GOAL-T3-HOSTED-TRUSTED-DELIVERY",
        }
    ]
    capacity = {
        "total_repository_lanes": (
            primary.reserved_trusted_lanes + primary.max_concurrent_verified_lanes
        ),
        "reserved_trusted_lanes": primary.reserved_trusted_lanes,
        "max_concurrent_verified_lanes": primary.max_concurrent_verified_lanes,
    }
    return primary.goal_id, concurrent, capacity


def _ready_tasks(graph: MissionTaskGraphV1, state: MissionExecutionStateV1) -> list[TaskCardV1]:
    ready = _dependency_ready_tasks(graph, state)
    primary, concurrent, _capacity = _derive_goal_selection(graph, state)
    permitted = {goal for goal in [primary, *concurrent] if goal is not None}
    ready = [task for task in ready if task.stage_goal_id in permitted]

    def sort_key(task: TaskCardV1) -> tuple[int, int, str]:
        goal_rank = 0 if task.stage_goal_id == primary else 1
        return goal_rank, _PRIORITY_ORDER[task.priority], task.task_id

    return sorted(ready, key=sort_key)


def evaluate_mission(
    graph: MissionTaskGraphV1, state: MissionExecutionStateV1
) -> MissionEvaluation:
    by_id = {task.task_id: task for task in graph.taskcards}

    def status_for(task: TaskCardV1) -> MissionTaskStatus:
        # `status` is intentionally read-only in the CLI. A newly governed
        # taskcard may therefore appear in the graph before the next
        # evaluate/claim/transition call has reconciled and persisted it.
        # Use the graph's declared status for that additive case; mutating
        # paths still merge it durably in `_load_or_initialize()`.
        return state.task_statuses.get(task.task_id, task.status)

    active = by_id.get(state.active_task_id) if state.active_task_id else None
    eligible = [] if active else _ready_tasks(graph, state)
    unresolved = [task.task_id for task in graph.taskcards if status_for(task) not in _TERMINAL]
    blocked_external = [
        task.task_id for task in graph.taskcards if status_for(task) == "BLOCKED_EXTERNAL"
    ]
    complete = (
        not unresolved
        and not blocked_external
        and all(status_for(task) == "CLOSED" for task in graph.taskcards)
    )
    active_goal_id, concurrent_goal_ids, capacity_allocation = _derive_goal_selection(graph, state)
    selected = active or (eligible[0] if eligible else None)
    next_task = (
        MissionNextTaskV1(
            task_id=selected.task_id,
            stage_goal_id=selected.stage_goal_id,
            goal_ids=selected.goal_ids,
            core_contribution=selected.core_contribution,
        )
        if selected is not None
        else None
    )
    return MissionEvaluation(
        mission_id=graph.mission_authority.mission_id,
        active_task=active,
        eligible_tasks=eligible,
        unresolved_task_ids=unresolved,
        blocked_external_task_ids=blocked_external,
        lifecycle_scoreboard=state.lifecycle_scoreboard,
        next_task=next_task,
        active_goal_id=active_goal_id,
        concurrent_goal_ids=concurrent_goal_ids,
        capacity_allocation=capacity_allocation,
        core_goal_active=not complete,
        mission_complete=complete,
    )


def _refresh_goal_state(
    backend: StateBackend,
    graph: MissionTaskGraphV1,
    state: MissionExecutionStateV1,
) -> MissionExecutionStateV1:
    scoreboard = derive_lifecycle_scoreboard(backend)
    with_scoreboard = state.model_copy(update={"lifecycle_scoreboard": scoreboard})
    evaluation = evaluate_mission(graph, with_scoreboard)
    goal_changed = (
        state.active_goal_id != evaluation.active_goal_id
        or state.concurrent_goal_ids != evaluation.concurrent_goal_ids
    )
    history = state.goal_history
    if goal_changed:
        history = [
            *history,
            MissionGoalTransitionV1(
                from_primary_goal_id=state.active_goal_id,
                to_primary_goal_id=evaluation.active_goal_id,
                from_concurrent_goal_ids=state.concurrent_goal_ids,
                to_concurrent_goal_ids=evaluation.concurrent_goal_ids,
                reason="derived from earliest incomplete stage and dependency-ready concurrency",
                graph_sha256=state.graph_sha256,
                occurred_at=datetime.now(UTC).isoformat(),
            ),
        ]
    return with_scoreboard.model_copy(
        update={
            "next_task": evaluation.next_task,
            "active_goal_id": evaluation.active_goal_id,
            "concurrent_goal_ids": evaluation.concurrent_goal_ids,
            "goal_history": history,
            "goal_activation_graph_sha256": state.graph_sha256,
            "goal_activation_reason": (
                "earliest incomplete governed stage with dependency-ready read-only look-ahead"
            ),
            "capacity_allocation": evaluation.capacity_allocation,
            "mission_complete": evaluation.mission_complete,
        }
    )


def _save_with_retry(
    backend: StateBackend,
    graph: MissionTaskGraphV1,
    graph_sha256: str,
    mutator,
) -> RunStateV1:
    for _ in range(3):
        record, expected = _load_or_initialize(backend, graph, graph_sha256)
        state = record.mission_execution
        assert state is not None
        next_state = _refresh_goal_state(backend, graph, mutator(state))
        if next_state == state:
            return record
        result = backend.save(
            mission_state_key(graph.mission_authority.mission_id),
            record.model_copy(update={"mission_execution": next_state}),
            expected,
        )
        if result.outcome == "saved":
            loaded = backend.load(mission_state_key(graph.mission_authority.mission_id))
            if loaded is None:
                raise StateBackendError("mission state disappeared immediately after save")
            return loaded
        if result.outcome != "stale":
            raise StateBackendError(f"mission state save failed: {result.outcome}")
    raise StateBackendError("mission state CAS remained stale after 3 reconciliation attempts")


def persist_evaluation(
    backend: StateBackend, graph: MissionTaskGraphV1, graph_sha256: str
) -> RunStateV1:
    return _save_with_retry(
        backend,
        graph,
        graph_sha256,
        lambda state: state.model_copy(
            update={
                "mission_complete": evaluate_mission(graph, state).mission_complete,
                "last_evaluated_at": datetime.now(UTC).isoformat(),
            }
        ),
    )


def claim_next_task(
    backend: StateBackend,
    graph: MissionTaskGraphV1,
    graph_sha256: str,
    *,
    claimed_by: str,
) -> RunStateV1:
    def claim(state: MissionExecutionStateV1) -> MissionExecutionStateV1:
        now = datetime.now(UTC)
        state = _recover_expired_claim(state, now)
        if state.active_task_id is not None:
            if state.claim_id is None or state.claimed_by == claimed_by:
                return state.model_copy(
                    update={
                        "claim_id": uuid4().hex,
                        "claimed_by": claimed_by,
                        "claimed_at": now.isoformat(),
                        "claim_expires_at": (now + _CLAIM_LEASE).isoformat(),
                        "last_evaluated_at": now.isoformat(),
                    }
                )
            return state
        ready = _ready_tasks(graph, state)
        if not ready:
            return state.model_copy(
                update={
                    "mission_complete": evaluate_mission(graph, state).mission_complete,
                    "last_evaluated_at": now.isoformat(),
                }
            )
        selected = ready[0]
        prior_status = state.task_statuses[selected.task_id]
        statuses = dict(state.task_statuses)
        statuses[selected.task_id] = "IN_PROGRESS"
        transition = MissionTransitionV1(
            task_id=selected.task_id,
            from_status=prior_status,
            to_status="IN_PROGRESS",
            observed_by=claimed_by,
            reason="deterministic highest-priority dependency-ready selection",
        )
        return state.model_copy(
            update={
                "task_statuses": statuses,
                "active_task_id": selected.task_id,
                "claim_id": uuid4().hex,
                "claimed_by": claimed_by,
                "claimed_at": now.isoformat(),
                "claim_expires_at": (now + _CLAIM_LEASE).isoformat(),
                "transition_history": [*state.transition_history, transition],
                "mission_complete": False,
                "last_evaluated_at": now.isoformat(),
            }
        )

    return _save_with_retry(backend, graph, graph_sha256, claim)


def transition_task(
    backend: StateBackend,
    graph: MissionTaskGraphV1,
    graph_sha256: str,
    *,
    task_id: str,
    to_status: MissionTaskStatus,
    observed_by: str,
    reason: str,
    evidence_refs: list[str],
) -> RunStateV1:
    graph_ids = {task.task_id for task in graph.taskcards}
    if task_id not in graph_ids:
        raise ConfigError(f"unknown mission task_id {task_id!r}")
    if to_status in {"IMPLEMENTED", "VERIFIED", "SCORED", "CLOSED"} and not evidence_refs:
        raise ConfigError(f"transition to {to_status} requires at least one evidence reference")
    task = next(task for task in graph.taskcards if task.task_id == task_id)

    def transition(state: MissionExecutionStateV1) -> MissionExecutionStateV1:
        from_status = state.task_statuses[task_id]
        if to_status not in _TRANSITIONS[from_status]:
            raise ConfigError(f"invalid mission transition {from_status} -> {to_status}")
        if to_status == "CLOSED":
            validate_task_contribution_evidence(
                task,
                evidence_refs,
                derive_lifecycle_scoreboard(backend),
            )
        if state.active_task_id not in {None, task_id}:
            raise ConfigError(
                f"task {task_id!r} cannot transition while {state.active_task_id!r} is active"
            )
        statuses = dict(state.task_statuses)
        statuses[task_id] = to_status
        terminal_or_review = to_status not in {"IN_PROGRESS"}
        history = [
            *state.transition_history,
            MissionTransitionV1(
                task_id=task_id,
                from_status=from_status,
                to_status=to_status,
                observed_by=observed_by,
                evidence_refs=evidence_refs,
                reason=reason,
            ),
        ]
        next_state = state.model_copy(
            update={
                "task_statuses": statuses,
                "active_task_id": None if terminal_or_review else task_id,
                "claim_id": None if terminal_or_review else state.claim_id,
                "claimed_by": None if terminal_or_review else state.claimed_by,
                "claimed_at": None if terminal_or_review else state.claimed_at,
                "claim_expires_at": None if terminal_or_review else state.claim_expires_at,
                "transition_history": history,
                "mission_complete": False,
                "last_evaluated_at": datetime.now(UTC).isoformat(),
            }
        )
        return next_state.model_copy(
            update={"mission_complete": evaluate_mission(graph, next_state).mission_complete}
        )

    return _save_with_retry(backend, graph, graph_sha256, transition)
