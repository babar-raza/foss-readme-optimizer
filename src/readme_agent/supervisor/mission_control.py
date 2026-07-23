"""Load, validate, claim, transition, and evaluate central mission taskcards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from readme_agent.errors import ConfigError, StateBackendError
from readme_agent.state.backend import StateBackend
from readme_agent.state.schema import (
    MissionExecutionStateV1,
    MissionTaskStatus,
    MissionTransitionV1,
    RunStateV1,
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
_DEPENDENCY_SATISFIED = _TERMINAL_SUCCESS | {"REROUTED"}
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
    mission_complete: bool


def mission_state_key(mission_id: str) -> str:
    """Dedicated namespace accepted by the existing per-key Git-ref backend."""
    return f"mission/{mission_id}"


def _initial_state(graph: MissionTaskGraphV1, graph_sha256: str) -> MissionExecutionStateV1:
    statuses = {task.task_id: task.status for task in graph.taskcards}
    active = [task.task_id for task in graph.taskcards if task.status == "IN_PROGRESS"]
    if len(active) > 1:
        raise ConfigError(f"mission graph has multiple IN_PROGRESS tasks: {active}")
    return MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_sha256,
        task_statuses=statuses,
        active_task_id=active[0] if active else None,
        claimed_by=graph.taskcards[0].owner if active else None,
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


def _ready_tasks(graph: MissionTaskGraphV1, state: MissionExecutionStateV1) -> list[TaskCardV1]:
    by_id = {task.task_id: task for task in graph.taskcards}
    ready: list[TaskCardV1] = []
    for task in graph.taskcards:
        status = state.task_statuses[task.task_id]
        if status not in {"TODO", "READY", "REOPENED", "REGRESSED"}:
            continue
        if all(
            state.task_statuses[dependency] in _DEPENDENCY_SATISFIED
            for dependency in task.dependencies
        ):
            ready.append(by_id[task.task_id])
    return sorted(ready, key=lambda task: (_PRIORITY_ORDER[task.priority], task.task_id))


def evaluate_mission(
    graph: MissionTaskGraphV1, state: MissionExecutionStateV1
) -> MissionEvaluation:
    by_id = {task.task_id: task for task in graph.taskcards}
    active = by_id.get(state.active_task_id) if state.active_task_id else None
    eligible = [] if active else _ready_tasks(graph, state)
    unresolved = [
        task.task_id
        for task in graph.taskcards
        if state.task_statuses[task.task_id] not in _TERMINAL
    ]
    blocked_external = [
        task.task_id
        for task in graph.taskcards
        if state.task_statuses[task.task_id] == "BLOCKED_EXTERNAL"
    ]
    complete = (
        not unresolved
        and not blocked_external
        and all(state.task_statuses[task.task_id] == "CLOSED" for task in graph.taskcards)
    )
    return MissionEvaluation(
        mission_id=graph.mission_authority.mission_id,
        active_task=active,
        eligible_tasks=eligible,
        unresolved_task_ids=unresolved,
        blocked_external_task_ids=blocked_external,
        mission_complete=complete,
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
        next_state = mutator(state)
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
        if state.active_task_id is not None:
            if state.claim_id is None:
                return state.model_copy(
                    update={
                        "claim_id": uuid4().hex,
                        "claimed_by": claimed_by,
                        "claimed_at": datetime.now(UTC).isoformat(),
                        "last_evaluated_at": datetime.now(UTC).isoformat(),
                    }
                )
            return state
        ready = _ready_tasks(graph, state)
        if not ready:
            return state.model_copy(
                update={
                    "mission_complete": evaluate_mission(graph, state).mission_complete,
                    "last_evaluated_at": datetime.now(UTC).isoformat(),
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
                "claimed_at": datetime.now(UTC).isoformat(),
                "transition_history": [*state.transition_history, transition],
                "mission_complete": False,
                "last_evaluated_at": datetime.now(UTC).isoformat(),
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

    def transition(state: MissionExecutionStateV1) -> MissionExecutionStateV1:
        from_status = state.task_statuses[task_id]
        if to_status not in _TRANSITIONS[from_status]:
            raise ConfigError(f"invalid mission transition {from_status} -> {to_status}")
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
                "transition_history": history,
                "mission_complete": False,
                "last_evaluated_at": datetime.now(UTC).isoformat(),
            }
        )
        return next_state.model_copy(
            update={"mission_complete": evaluate_mission(graph, next_state).mission_complete}
        )

    return _save_with_retry(backend, graph, graph_sha256, transition)
