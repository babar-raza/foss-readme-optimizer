"""Bind visible repository execution to the current durable mission focus."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from readme_agent.errors import ConfigError
from readme_agent.state.backend import StateBackend
from readme_agent.supervisor.approach_control import decide_approach_admission
from readme_agent.supervisor.mission_control import mission_state_key
from readme_agent.supervisor.mission_graph import load_mission_graph

DEFAULT_MISSION_GRAPH = (
    Path(__file__).resolve().parents[3]
    / "plans"
    / "investigations"
    / "control"
    / "level8-autonomous-mission-task-graph.yaml"
)


def _parse_timestamp(value: str | None, label: str) -> datetime:
    if value is None:
        raise ConfigError(f"active mission execution has no {label}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ConfigError(f"active mission execution has invalid {label}") from exc
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def require_visible_execution_binding(
    backend: StateBackend,
    *,
    task_id: str | None,
    repository: str,
    observer: str,
    graph_path: Path = DEFAULT_MISSION_GRAPH,
    now: datetime | None = None,
) -> str:
    """Reject a canary that is not the current claimed small delivery goal."""

    if not task_id:
        raise ConfigError(
            "bounded verified execution requires --mission-task-id for the active small goal"
        )
    graph, graph_sha256 = load_mission_graph(graph_path)
    task = next((item for item in graph.taskcards if item.task_id == task_id), None)
    if task is None:
        raise ConfigError(f"mission task {task_id!r} is not in the active graph")
    focus = task.execution_focus
    if focus is None:
        raise ConfigError(f"mission task {task_id!r} has no executable delivery focus")
    if repository not in focus.repository_scope:
        raise ConfigError(
            f"repository {repository!r} is outside immediate goal {focus.goal_id!r}: "
            f"{focus.repository_scope}"
        )

    record = backend.load(mission_state_key(graph.mission_authority.mission_id))
    if record is None or record.mission_execution is None:
        raise ConfigError(
            "durable mission state is unavailable; evaluate and claim before execution"
        )
    state = record.mission_execution
    if state.graph_sha256 != graph_sha256:
        raise ConfigError("durable mission state has graph drift; evaluate before execution")
    if state.active_task_id != task_id:
        raise ConfigError(
            f"task {task_id!r} is not the active mission task {state.active_task_id!r}"
        )
    if state.task_statuses.get(task_id) != "IN_PROGRESS":
        raise ConfigError(f"active mission task {task_id!r} is not IN_PROGRESS")
    if state.claimed_by != observer:
        raise ConfigError(
            f"task {task_id!r} is claimed by {state.claimed_by!r}, not observer {observer!r}"
        )
    expires_at = _parse_timestamp(state.claim_expires_at, "claim_expires_at")
    if expires_at <= (now or datetime.now(UTC)):
        raise ConfigError("active mission claim expired; reclaim through the mission controller")
    decision = decide_approach_admission(state.approach_control, task, now=now)
    if not decision.admitted:
        raise ConfigError(decision.reason)
    return focus.goal_id
