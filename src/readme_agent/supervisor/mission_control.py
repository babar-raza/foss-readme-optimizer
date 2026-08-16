"""Load, validate, claim, transition, and evaluate central mission taskcards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from readme_agent.errors import ConfigError, StateBackendError
from readme_agent.state.agile_execution_schema import (
    FirstPrinciplesReplanV1,
    ParallelismObservationV1,
)
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
from readme_agent.supervisor.approach_control import (
    apply_first_principles_replan,
    decide_approach_admission,
    finish_latest_attempt,
    record_material_narrowing,
    start_approach_attempt,
    validate_approach_closeout,
)
from readme_agent.supervisor.infrastructure_admission import (
    decide_infrastructure_admission,
    task_execution_kind,
)
from readme_agent.supervisor.mission_goal_guard import (
    derive_lifecycle_scoreboard,
    validate_task_contribution_evidence,
)
from readme_agent.supervisor.mission_schema import MissionTaskGraphV1, TaskCardV1
from readme_agent.supervisor.multi_agent_admission import validate_multi_agent_closeout_binding
from readme_agent.supervisor.parallelism_admission import decide_parallelism

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
_BACKGROUND_CERTIFICATION_GOALS: set[StageGoalId] = {
    "GOAL-L7-HETEROGENEOUS-30D",
    "GOAL-L8-SELF-MAINTAINING-90D",
}
_TRANSITIONS: dict[MissionTaskStatus, set[MissionTaskStatus]] = {
    "TODO": {
        "READY",
        "BLOCKED",
        "BLOCKED_EXTERNAL",
        "DEFERRED_WITH_REASON",
        "OBSERVATION_RUNNING",
    },
    "READY": {
        "IN_PROGRESS",
        "BLOCKED",
        "BLOCKED_EXTERNAL",
        "DEFERRED_WITH_REASON",
        "OBSERVATION_RUNNING",
    },
    "IN_PROGRESS": {"IMPLEMENTED", "BLOCKED", "BLOCKED_EXTERNAL", "REROUTED", "REGRESSED"},
    "IMPLEMENTED": {"VERIFIED", "REOPENED", "REGRESSED"},
    "VERIFIED": {"SCORED", "REOPENED", "REGRESSED"},
    "SCORED": {"CLOSED", "REOPENED", "REGRESSED"},
    "CLOSED": {"REOPENED", "REGRESSED"},
    "BLOCKED": {"READY", "REROUTED", "BLOCKED_EXTERNAL"},
    "BLOCKED_EXTERNAL": {"REOPENED"},
    "REROUTED": {"READY", "DEFERRED_WITH_REASON"},
    "DEFERRED_WITH_REASON": {"REOPENED", "OBSERVATION_RUNNING"},
    "OBSERVATION_RUNNING": {"CLOSED", "REGRESSED"},
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
    delivery_complete: bool
    certification_complete: bool
    mission_complete: bool


def mission_state_key(mission_id: str) -> str:
    """Dedicated namespace accepted by the existing per-key Git-ref backend."""
    return f"mission/{mission_id}"


def _initial_state(graph: MissionTaskGraphV1, graph_sha256: str) -> MissionExecutionStateV1:
    statuses = {task.task_id: task.status for task in graph.taskcards}
    statuses.update({task.task_id: task.status for task in graph.deferred_task_index})
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
    latest_attempt = next(
        (
            attempt
            for attempt in reversed(state.approach_control.attempts)
            if attempt.task_id == task_id and attempt.outcome == "in_progress"
        ),
        None,
    )
    prior_narrowing = latest_attempt.last_material_narrowing_at if latest_attempt else None
    prior_evidence = list(latest_attempt.evidence_refs) if latest_attempt else []
    approach_control = finish_latest_attempt(
        state.approach_control,
        task_id,
        effective=prior_narrowing is not None,
        evidence_refs=list(dict.fromkeys([*prior_evidence, "claim lease expired"])),
        narrowed_at=prior_narrowing,
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
            "approach_control": approach_control,
            "parallelism_control": state.parallelism_control.model_copy(
                update={"shared_repair_active": False}
            ),
            "last_evaluated_at": now.isoformat(),
        }
    )


def _apply_deferred_dispositions(
    state: MissionExecutionStateV1,
    graph: MissionTaskGraphV1,
    now: datetime,
) -> MissionExecutionStateV1:
    """Migrate newly archived work without deleting its durable history."""

    deferred_ids = {
        task.task_id for task in graph.deferred_task_index if task.status == "DEFERRED_WITH_REASON"
    }
    statuses = dict(state.task_statuses)
    history = list(state.transition_history)
    active_task_id = state.active_task_id
    changed = False
    for task_id in sorted(deferred_ids):
        prior = statuses.get(task_id)
        if prior in {None, "CLOSED", "DEFERRED_WITH_REASON"}:
            continue
        statuses[task_id] = "DEFERRED_WITH_REASON"
        history.append(
            MissionTransitionV1(
                task_id=task_id,
                from_status=prior,
                to_status="DEFERRED_WITH_REASON",
                observed_by="mission-graph-migration",
                reason=(
                    "compact authority archived historical control work with an explicit "
                    "non-executable disposition"
                ),
            )
        )
        if active_task_id == task_id:
            active_task_id = None
        changed = True
    if not changed:
        return state
    clear_claim = state.active_task_id != active_task_id
    return state.model_copy(
        update={
            "task_statuses": statuses,
            "active_task_id": active_task_id,
            "claim_id": None if clear_claim else state.claim_id,
            "claimed_by": None if clear_claim else state.claimed_by,
            "claimed_at": None if clear_claim else state.claimed_at,
            "claim_expires_at": None if clear_claim else state.claim_expires_at,
            "transition_history": history,
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
    graph_ids.update(task.task_id for task in graph.deferred_task_index)
    unknown = set(state.task_statuses) - graph_ids
    if unknown:
        raise StateBackendError(
            f"durable mission state contains orphan task IDs: {sorted(unknown)}"
        )
    merged = dict(state.task_statuses)
    for task in graph.taskcards:
        merged.setdefault(task.task_id, task.status)
    for deferred_task in graph.deferred_task_index:
        merged.setdefault(deferred_task.task_id, deferred_task.status)
    now = datetime.now(UTC)
    state = _apply_deferred_dispositions(
        state.model_copy(update={"task_statuses": merged}), graph, now
    )
    reconciled = state.model_copy(
        update={
            "graph_sha256": graph_sha256,
            "last_evaluated_at": now.isoformat(),
        }
    )
    return record.model_copy(update={"mission_execution": reconciled}), record.state_version


def _dependency_ready_tasks(
    graph: MissionTaskGraphV1, state: MissionExecutionStateV1
) -> list[TaskCardV1]:
    by_id = {task.task_id: task for task in graph.taskcards}
    deferred_status_by_id = {task.task_id: task.status for task in graph.deferred_task_index}

    def status_for(task_id: str) -> MissionTaskStatus:
        task = by_id.get(task_id)
        if task is not None:
            return state.task_statuses.get(task_id, task.status)
        # A dependency may point at a retired-but-satisfied task that now lives
        # only in the deferred catalog (see l8-horizon-01-deferral-2026-08-13
        # Finding 3): resolve its status there instead of treating it as unknown.
        return state.task_statuses.get(task_id, deferred_status_by_id[task_id])

    ready: list[TaskCardV1] = []
    python_task = by_id.get("L8-VPY-03-ALL-PYTHON-VERIFIED-POC")
    python_complete = python_task is not None and status_for(python_task.task_id) == "CLOSED"
    for task in graph.taskcards:
        status = status_for(task.task_id)
        if status not in {"TODO", "READY", "REOPENED", "REGRESSED"}:
            continue
        if not all(
            status_for(dependency) in _DEPENDENCY_SATISFIED for dependency in task.dependencies
        ):
            continue
        infrastructure = decide_infrastructure_admission(
            task,
            infrastructure_tasks_since_visible_delivery=(
                state.infrastructure_tasks_since_visible_delivery
            ),
            python_platform_complete=python_complete,
        )
        approach = decide_approach_admission(state.approach_control, task)
        if infrastructure.admitted and approach.admitted:
            ready.append(by_id[task.task_id])
    return ready


def _derive_goal_selection(
    graph: MissionTaskGraphV1,
    state: MissionExecutionStateV1,
) -> tuple[StageGoalId | None, list[StageGoalId], dict[str, int]]:
    """Derive primary/concurrent goals from task truth, never narrative selection."""

    goals = sorted(graph.mission_authority.stage_goal_catalog, key=lambda goal: goal.order)
    # Deferred (out-of-active-scope, per Decision #93 compact authority) tasks
    # never drive near-term primary-goal selection -- only the active graph
    # represents current claimable work. A goal whose active representation is
    # fully terminal is not "primary" just because unpromoted backlog sits at
    # the same stage; evaluate_mission's delivery_complete/unresolved_task_ids
    # separately -- and correctly -- still require that backlog to close.
    task_statuses_by_goal: dict[StageGoalId, list[MissionTaskStatus]] = {
        goal.goal_id: [] for goal in goals
    }
    for task in graph.taskcards:
        task_statuses_by_goal[task.stage_goal_id].append(
            state.task_statuses.get(task.task_id, task.status)
        )

    def status_for(task: TaskCardV1) -> MissionTaskStatus:
        return state.task_statuses.get(task.task_id, task.status)

    incomplete = [
        goal
        for goal in goals
        if goal.execution_required
        and any(status not in _TERMINAL for status in task_statuses_by_goal[goal.goal_id])
    ]
    primary = incomplete[0] if incomplete else None
    if primary is None:
        return None, [], {}
    ready = _dependency_ready_tasks(graph, state)
    parallelism = decide_parallelism(state.parallelism_control)
    admitted_lanes = min(
        primary.max_concurrent_verified_lanes,
        parallelism.max_repository_lanes,
    )
    concurrent = [
        goal.goal_id
        for goal in incomplete[1:]
        if goal.concurrent_when_earlier_primary
        and any(
            task.stage_goal_id == goal.goal_id
            and task.concurrency_class
            in {"read_only_assurance_isolated", "repository_local_write_isolated"}
            for task in ready
        )
        and admitted_lanes > 1
    ]
    capacity = {
        "total_repository_lanes": (primary.reserved_trusted_lanes + admitted_lanes),
        "reserved_trusted_lanes": primary.reserved_trusted_lanes,
        "max_concurrent_verified_lanes": admitted_lanes,
        "policy_max_repository_lanes": parallelism.max_repository_lanes,
    }
    return primary.goal_id, concurrent, capacity


def _ready_tasks(graph: MissionTaskGraphV1, state: MissionExecutionStateV1) -> list[TaskCardV1]:
    ready = _dependency_ready_tasks(graph, state)
    primary, concurrent, _capacity = _derive_goal_selection(graph, state)
    permitted = {goal for goal in [primary, *concurrent] if goal is not None}
    ready = [task for task in ready if task.stage_goal_id in permitted]

    campaign_order = {campaign.campaign_id: campaign.order for campaign in graph.campaign_catalog}

    def sort_key(task: TaskCardV1) -> tuple[int, int, int, str]:
        goal_rank = 0 if task.stage_goal_id == primary else 1
        campaign_rank = (
            campaign_order[task.campaign_id]
            if task.campaign_id is not None
            else len(campaign_order) + 1
        )
        return goal_rank, campaign_rank, _PRIORITY_ORDER[task.priority], task.task_id

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
    required_goal_ids = {
        goal.goal_id
        for goal in graph.mission_authority.stage_goal_catalog
        if goal.execution_required
    }
    required_tasks = [task for task in graph.taskcards if task.stage_goal_id in required_goal_ids]
    required_deferred = [
        task
        for task in graph.deferred_task_index
        if task.stage_goal_id in required_goal_ids and task.activation_group != "historical-control"
    ]
    unresolved = [task.task_id for task in required_tasks if status_for(task) not in _TERMINAL]
    unresolved.extend(
        task.task_id
        for task in required_deferred
        if state.task_statuses.get(task.task_id, task.status) not in _TERMINAL
    )
    blocked_external = [
        task.task_id for task in required_tasks if status_for(task) == "BLOCKED_EXTERNAL"
    ]
    blocked_external.extend(
        task.task_id
        for task in required_deferred
        if state.task_statuses.get(task.task_id, task.status) == "BLOCKED_EXTERNAL"
    )
    delivery_complete = (
        not unresolved
        and not blocked_external
        and all(status_for(task) == "CLOSED" for task in required_tasks)
        and all(
            state.task_statuses.get(task.task_id, task.status) == "CLOSED"
            for task in required_deferred
        )
    )
    all_task_statuses = {
        **{task.task_id: status_for(task) for task in graph.taskcards},
        **{
            task.task_id: state.task_statuses.get(task.task_id, task.status)
            for task in graph.deferred_task_index
        },
    }
    certification_task_ids = {
        task.task_id
        for task in graph.taskcards
        if task.stage_goal_id in _BACKGROUND_CERTIFICATION_GOALS
    }
    certification_task_ids.update(
        task.task_id
        for task in graph.deferred_task_index
        if task.stage_goal_id in _BACKGROUND_CERTIFICATION_GOALS
    )
    certification_complete = bool(certification_task_ids) and all(
        all_task_statuses[task_id] == "CLOSED" for task_id in certification_task_ids
    )
    complete = delivery_complete and certification_complete
    active_goal_id, concurrent_goal_ids, capacity_allocation = _derive_goal_selection(graph, state)
    selected = active or next(
        (task for task in eligible if task.stage_goal_id == active_goal_id),
        None,
    )
    next_task = (
        MissionNextTaskV1(
            task_id=selected.task_id,
            stage_goal_id=selected.stage_goal_id,
            campaign_id=selected.campaign_id,
            goal_ids=selected.goal_ids,
            core_contribution=selected.core_contribution,
            immediate_goal_id=(
                selected.execution_focus.goal_id if selected.execution_focus else None
            ),
            immediate_outcome=(
                selected.execution_focus.immediate_outcome if selected.execution_focus else None
            ),
            repository_scope=(
                selected.execution_focus.repository_scope if selected.execution_focus else []
            ),
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
        delivery_complete=delivery_complete,
        certification_complete=certification_complete,
        mission_complete=complete,
    )


def _regress_stale_closed_repository_deliverables(
    graph: MissionTaskGraphV1,
    state: MissionExecutionStateV1,
    scoreboard: MissionLifecycleScoreboardV1,
) -> MissionExecutionStateV1:
    stale = {
        **scoreboard.stale_fact_contract_repositories,
        **scoreboard.stale_acceptance_repositories,
    }
    if not stale:
        return state
    statuses = dict(state.task_statuses)
    history = list(state.transition_history)
    task_scopes = {
        task.task_id: set(task.execution_focus.repository_scope)
        for task in graph.taskcards
        if task.execution_focus is not None
    }
    for org_repo in sorted(stale):
        scoped_tasks = [
            task for task in graph.taskcards if org_repo in task_scopes.get(task.task_id, set())
        ]
        if any(statuses.get(task.task_id, task.status) != "CLOSED" for task in scoped_tasks):
            continue
        closed = [
            task for task in scoped_tasks if statuses.get(task.task_id, task.status) == "CLOSED"
        ]
        if not closed:
            continue
        task = closed[-1]
        statuses[task.task_id] = "REGRESSED"
        history.append(
            MissionTransitionV1(
                task_id=task.task_id,
                from_status="CLOSED",
                to_status="REGRESSED",
                observed_by="mission-lifecycle-freshness",
                reason=(
                    f"repository deliverable became stale for {org_repo}: "
                    + ",".join(stale[org_repo])
                ),
            )
        )
    if statuses == state.task_statuses:
        return state
    return state.model_copy(
        update={
            "task_statuses": statuses,
            "transition_history": history,
            "mission_complete": False,
        }
    )


def _refresh_goal_state(
    backend: StateBackend,
    graph: MissionTaskGraphV1,
    state: MissionExecutionStateV1,
    *,
    scoreboard: MissionLifecycleScoreboardV1 | None = None,
) -> MissionExecutionStateV1:
    scoreboard = scoreboard or derive_lifecycle_scoreboard(backend)
    with_scoreboard = _regress_stale_closed_repository_deliverables(
        graph,
        state.model_copy(update={"lifecycle_scoreboard": scoreboard}),
        scoreboard,
    )
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
            "delivery_complete": evaluation.delivery_complete,
            "certification_complete": evaluation.certification_complete,
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
        scoreboard = derive_lifecycle_scoreboard(backend)
        reconciled = _refresh_goal_state(backend, graph, state, scoreboard=scoreboard)
        next_state = _refresh_goal_state(
            backend,
            graph,
            mutator(reconciled),
            scoreboard=scoreboard,
        )
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
    expected_task_id: str | None = None,
) -> RunStateV1:
    if expected_task_id is not None and expected_task_id not in {
        task.task_id for task in graph.taskcards
    }:
        raise ConfigError(f"unknown expected mission task_id {expected_task_id!r}")

    def claim(state: MissionExecutionStateV1) -> MissionExecutionStateV1:
        now = datetime.now(UTC)
        state = _recover_expired_claim(state, now)
        if state.active_task_id is not None:
            if expected_task_id is not None and state.active_task_id != expected_task_id:
                raise ConfigError(
                    f"expected mission task {expected_task_id!r}, but "
                    f"{state.active_task_id!r} owns the active claim"
                )
            active_task = next(
                task for task in graph.taskcards if task.task_id == state.active_task_id
            )
            approach = decide_approach_admission(
                state.approach_control,
                active_task,
                now=now,
            )
            if not approach.admitted:
                raise ConfigError(approach.reason)
            if state.claim_id is None or state.claimed_by == claimed_by:
                try:
                    approach_control = start_approach_attempt(
                        state.approach_control,
                        active_task,
                        now=now,
                    )
                except ValueError as exc:
                    raise ConfigError(
                        f"task {active_task.task_id!r} approach admission failed: {exc}"
                    ) from exc
                return state.model_copy(
                    update={
                        "claim_id": uuid4().hex,
                        "claimed_by": claimed_by,
                        "claimed_at": now.isoformat(),
                        "claim_expires_at": (now + _CLAIM_LEASE).isoformat(),
                        "approach_control": approach_control,
                        "last_evaluated_at": now.isoformat(),
                    }
                )
            return state
        ready = _ready_tasks(graph, state)
        primary_goal, _concurrent_goals, _capacity = _derive_goal_selection(graph, state)
        claimable = [task for task in ready if task.stage_goal_id == primary_goal]
        if not claimable or (
            expected_task_id is not None
            and expected_task_id not in {task.task_id for task in claimable}
        ):
            # A just-recovered expired claim (above) must persist even when the
            # specifically requested task cannot be claimed this attempt --
            # otherwise every retry recomputes and discards the same recovery
            # forever. claim_next_task() reports the mismatch to the caller
            # from this already-persisted state instead of raising here.
            return state.model_copy(
                update={
                    "mission_complete": evaluate_mission(graph, state).mission_complete,
                    "last_evaluated_at": now.isoformat(),
                }
            )
        selected = (
            claimable[0]
            if expected_task_id is None
            else next(task for task in claimable if task.task_id == expected_task_id)
        )
        try:
            approach_control = start_approach_attempt(
                state.approach_control,
                selected,
                now=now,
            )
        except ValueError as exc:
            raise ConfigError(
                f"task {selected.task_id!r} approach admission failed: {exc}"
            ) from exc
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
                "approach_control": approach_control,
                "parallelism_control": state.parallelism_control.model_copy(
                    update={
                        "shared_repair_active": task_execution_kind(selected) == "shared_repair"
                    }
                ),
                "mission_complete": False,
                "last_evaluated_at": now.isoformat(),
            }
        )

    record = _save_with_retry(backend, graph, graph_sha256, claim)
    if expected_task_id is not None and (
        record.mission_execution is None
        or record.mission_execution.active_task_id != expected_task_id
    ):
        state = record.mission_execution
        assert state is not None
        ready = _ready_tasks(graph, state)
        primary_goal, _concurrent_goals, _capacity = _derive_goal_selection(graph, state)
        claimable = [task for task in ready if task.stage_goal_id == primary_goal]
        if not claimable:
            raise ConfigError(
                f"expected mission task {expected_task_id!r} is not dependency-ready "
                "or is blocked by primary-goal admission controls"
            )
        ready_ids = ", ".join(task.task_id for task in claimable) or "none"
        raise ConfigError(
            f"expected mission task {expected_task_id!r} is not eligible; "
            f"primary-goal eligible tasks: {ready_ids}"
        )
    return record


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
    if (
        to_status == "OBSERVATION_RUNNING"
        and task.stage_goal_id not in _BACKGROUND_CERTIFICATION_GOALS
    ):
        raise ConfigError(
            "OBSERVATION_RUNNING is reserved for Level-7/Level-8 background "
            f"certification tasks; {task_id!r} belongs to {task.stage_goal_id!r}"
        )

    def transition(state: MissionExecutionStateV1) -> MissionExecutionStateV1:
        now = datetime.now(UTC)
        from_status = state.task_statuses[task_id]
        if to_status not in _TRANSITIONS[from_status]:
            raise ConfigError(f"invalid mission transition {from_status} -> {to_status}")
        closeout_control = None
        if to_status == "CLOSED":
            try:
                validate_approach_closeout(state.approach_control, task, now=now)
            except ValueError as exc:
                raise ConfigError(f"task {task_id!r} approach closeout failed: {exc}") from exc
            _, closeout_control = validate_task_contribution_evidence(
                task,
                evidence_refs,
                derive_lifecycle_scoreboard(backend),
            )
            try:
                validate_multi_agent_closeout_binding(
                    task_id,
                    closeout_control,
                    decide_parallelism(state.parallelism_control),
                    repository_root=Path("."),
                )
            except ValueError as exc:
                raise ConfigError(f"task {task_id!r} multi-agent closeout failed: {exc}") from exc
        if state.active_task_id not in {None, task_id}:
            raise ConfigError(
                f"task {task_id!r} cannot transition while {state.active_task_id!r} is active"
            )
        statuses = dict(state.task_statuses)
        statuses[task_id] = to_status
        terminal_or_review = to_status not in {"IN_PROGRESS"}
        approach_control = state.approach_control
        if to_status == "IMPLEMENTED":
            approach_control = finish_latest_attempt(
                approach_control,
                task_id,
                effective=True,
                evidence_refs=evidence_refs,
                narrowed_at=now.isoformat(),
            )
        elif to_status in {"BLOCKED", "REGRESSED"}:
            approach_control = finish_latest_attempt(
                approach_control,
                task_id,
                effective=False,
                evidence_refs=evidence_refs or [reason],
            )
        elif to_status in {"BLOCKED_EXTERNAL", "REROUTED"}:
            # Reaching a governed external boundary or reroute is material narrowing,
            # not an equivalent failed technical attempt.
            approach_control = finish_latest_attempt(
                approach_control,
                task_id,
                effective=True,
                evidence_refs=evidence_refs or [reason],
                narrowed_at=now.isoformat(),
            )
        infrastructure_count = state.infrastructure_tasks_since_visible_delivery
        parallelism_control = state.parallelism_control
        if to_status == "CLOSED":
            kind = task_execution_kind(task)
            if kind == "visible_delivery":
                infrastructure_count = 0
            elif kind in {"infrastructure", "shared_repair"}:
                infrastructure_count += 1
            if closeout_control is not None and closeout_control.transaction_isolation_proven:
                parallelism_control = parallelism_control.model_copy(
                    update={
                        "transaction_isolation_proven": True,
                        "calibration_active": False,
                    }
                )
        if terminal_or_review and task_execution_kind(task) == "shared_repair":
            parallelism_control = parallelism_control.model_copy(
                update={"shared_repair_active": False}
            )
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
                "approach_control": approach_control,
                "infrastructure_tasks_since_visible_delivery": infrastructure_count,
                "parallelism_control": parallelism_control,
                "mission_complete": False,
                "last_evaluated_at": now.isoformat(),
            }
        )
        return next_state.model_copy(
            update={"mission_complete": evaluate_mission(graph, next_state).mission_complete}
        )

    return _save_with_retry(backend, graph, graph_sha256, transition)


def record_task_material_narrowing(
    backend: StateBackend,
    graph: MissionTaskGraphV1,
    graph_sha256: str,
    *,
    task_id: str,
    evidence_refs: list[str],
) -> RunStateV1:
    """Persist progress that resets the fifteen-minute anti-stall watermark."""

    if not evidence_refs:
        raise ConfigError("material narrowing requires at least one evidence reference")

    def update(state: MissionExecutionStateV1) -> MissionExecutionStateV1:
        if state.active_task_id != task_id:
            raise ConfigError(f"task {task_id!r} is not the active mission task")
        try:
            control = record_material_narrowing(
                state.approach_control,
                task_id,
                evidence_refs=evidence_refs,
            )
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc
        return state.model_copy(
            update={
                "approach_control": control,
                "last_evaluated_at": datetime.now(UTC).isoformat(),
            }
        )

    return _save_with_retry(backend, graph, graph_sha256, update)


def record_first_principles_replan(
    backend: StateBackend,
    graph: MissionTaskGraphV1,
    graph_sha256: str,
    *,
    replan: FirstPrinciplesReplanV1,
) -> RunStateV1:
    """Persist one structured, evidence-backed causal route change in mission state."""

    graph_task_ids = {task.task_id for task in graph.taskcards}
    if replan.task_id not in graph_task_ids:
        raise ConfigError(f"unknown mission task_id {replan.task_id!r}")
    missing = [reference for reference in replan.evidence_refs if not Path(reference).exists()]
    if missing:
        raise ConfigError(f"first-principles replan evidence does not exist: {missing}")
    task = next(task for task in graph.taskcards if task.task_id == replan.task_id)

    def update(state: MissionExecutionStateV1) -> MissionExecutionStateV1:
        task_status = state.task_statuses[replan.task_id]
        if task_status not in {"IN_PROGRESS", "READY", "REOPENED", "REGRESSED", "BLOCKED"}:
            raise ConfigError(
                f"task {replan.task_id!r} cannot be replanned from status {task_status!r}"
            )
        control = finish_latest_attempt(
            state.approach_control,
            replan.task_id,
            effective=False,
            evidence_refs=replan.evidence_refs,
        )
        try:
            control = apply_first_principles_replan(control, replan)
            if state.active_task_id == replan.task_id:
                control = start_approach_attempt(control, task)
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc
        return state.model_copy(
            update={
                "approach_control": control,
                "last_evaluated_at": datetime.now(UTC).isoformat(),
            }
        )

    return _save_with_retry(backend, graph, graph_sha256, update)


def record_parallelism_observation(
    backend: StateBackend,
    graph: MissionTaskGraphV1,
    graph_sha256: str,
    *,
    observation: ParallelismObservationV1,
) -> RunStateV1:
    """Append a measured lane result; the derived admission policy consumes it."""

    def update(state: MissionExecutionStateV1) -> MissionExecutionStateV1:
        control = state.parallelism_control
        if not control.transaction_isolation_proven:
            raise ConfigError("parallel observation requires prior transaction-isolation proof")
        if any(item.observed_at == observation.observed_at for item in control.observations):
            raise ConfigError("parallel observation is already recorded")
        return state.model_copy(
            update={
                "parallelism_control": control.model_copy(
                    update={"observations": [*control.observations, observation]}
                ),
                "last_evaluated_at": datetime.now(UTC).isoformat(),
            }
        )

    return _save_with_retry(backend, graph, graph_sha256, update)
