"""Load and validate the supervisor's declarative central mission graph."""

import hashlib
from pathlib import Path

import yaml

from readme_agent.errors import ConfigError
from readme_agent.supervisor.mission_schema import MissionTaskGraphV1, TaskCardV1


def load_mission_graph(path: Path) -> tuple[MissionTaskGraphV1, str]:
    """Load one escape-safe YAML graph and return it with its byte hash."""
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ConfigError(f"cannot read mission task graph {path}: {exc}") from exc
    try:
        raw = yaml.safe_load(payload)
        graph = MissionTaskGraphV1.model_validate(raw)
    except (yaml.YAMLError, ValueError, TypeError) as exc:
        raise ConfigError(f"invalid mission task graph {path}: {exc}") from exc
    _validate_graph(graph)
    return graph, hashlib.sha256(payload).hexdigest()


def _validate_graph(graph: MissionTaskGraphV1) -> None:
    contract = graph.autonomous_execution_contract
    authority = graph.mission_authority
    if not contract.mechanism_locked or contract.mechanism_type != "autonomous_supervision":
        raise ConfigError("mission must stay locked to autonomous_supervision")
    if not authority.mission_locked:
        raise ConfigError("mission_authority.mission_locked must be true")

    by_id: dict[str, TaskCardV1] = {}
    for task in graph.taskcards:
        if task.task_id in by_id:
            raise ConfigError(f"duplicate mission task_id {task.task_id!r}")
        if task.mission_id != authority.mission_id:
            raise ConfigError(
                f"task {task.task_id!r} belongs to {task.mission_id!r}, "
                f"not mission {authority.mission_id!r}"
            )
        by_id[task.task_id] = task

    for task in graph.taskcards:
        missing = [dependency for dependency in task.dependencies if dependency not in by_id]
        if missing:
            raise ConfigError(f"task {task.task_id!r} has unknown dependencies {missing}")
        if task.parent_task_id is not None and task.parent_task_id not in by_id:
            raise ConfigError(
                f"task {task.task_id!r} has unknown parent_task_id {task.parent_task_id!r}"
            )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ConfigError(f"cycle detected in mission task graph at {task_id!r}")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in by_id[task_id].dependencies:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in by_id:
        visit(task_id)
