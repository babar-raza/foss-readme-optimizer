"""Load and validate the supervisor's declarative central mission graph."""

import hashlib
from pathlib import Path

import yaml

from readme_agent.errors import ConfigError
from readme_agent.supervisor.mission_schema import MissionTaskGraphV1, TaskCardV1

_SUBORDINATE_GOAL_IDS = {
    "GOAL-TRUTH",
    "GOAL-README",
    "GOAL-PROFILE",
    "GOAL-AUTONOMY",
    "GOAL-DELIVERY",
    "GOAL-MATURITY",
}
_STAGE_GOAL_ORDERS = {
    "GOAL-T0-TRUSTED-QUALIFICATION": 10,
    "GOAL-C0-AUTHORIZED-PORTFOLIO": 15,
    "GOAL-T1-TRUSTED-PORTFOLIO": 20,
    "GOAL-T2-WORKFLOW-STAGING": 30,
    "GOAL-T3-HOSTED-TRUSTED-DELIVERY": 40,
    "GOAL-V1-VERIFIED-TRUTH": 50,
    "GOAL-V2-VERIFIED-GATE-A": 60,
    "GOAL-V3-HUMAN-AND-JAVA-PROOF": 70,
    "GOAL-L5-PRESENTATION-PILOT": 80,
    "GOAL-L6-AUTONOMOUS-PORTFOLIO": 90,
    "GOAL-L7-HETEROGENEOUS-30D": 100,
    "GOAL-L8-SELF-MAINTAINING-90D": 110,
}
_VAGUE_CONTRIBUTIONS = {
    "complete the task",
    "complete the task and support the mission",
    "improve the system",
    "support the mission",
    "continue the plan",
    "tbd",
}


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
    if authority.core_goal_id is not None or authority.goal_catalog:
        raise ConfigError("legacy universal mission goals must be absent after TRP-00 migration")
    stage_goals = authority.stage_goal_catalog
    stage_goal_ids = [goal.goal_id for goal in stage_goals]
    if len(stage_goal_ids) != len(set(stage_goal_ids)):
        raise ConfigError("mission stage_goal_catalog contains duplicate goal IDs")
    if {goal.goal_id: goal.order for goal in stage_goals} != _STAGE_GOAL_ORDERS:
        raise ConfigError("mission stage_goal_catalog does not match the governed ordered catalog")

    by_id: dict[str, TaskCardV1] = {}
    for task in graph.taskcards:
        if task.task_id in by_id:
            raise ConfigError(f"duplicate mission task_id {task.task_id!r}")
        if task.mission_id != authority.mission_id:
            raise ConfigError(
                f"task {task.task_id!r} belongs to {task.mission_id!r}, "
                f"not mission {authority.mission_id!r}"
            )
        if len(task.goal_ids) != len(set(task.goal_ids)):
            raise ConfigError(f"task {task.task_id!r} has duplicate goal_ids")
        if not set(task.goal_ids) <= _SUBORDINATE_GOAL_IDS:
            raise ConfigError(f"task {task.task_id!r} has an unknown subordinate goal")
        if task.stage_goal_id not in _STAGE_GOAL_ORDERS:
            raise ConfigError(f"task {task.task_id!r} has an unknown stage goal")
        stage_goal = next(goal for goal in stage_goals if goal.goal_id == task.stage_goal_id)
        if (
            task.concurrency_class == "read_only_assurance_isolated"
            and not stage_goal.concurrent_when_trusted_primary
        ):
            raise ConfigError(
                f"task {task.task_id!r} declares concurrent execution under a non-concurrent goal"
            )
        summary = " ".join(task.core_contribution.summary.lower().split())
        if summary in _VAGUE_CONTRIBUTIONS:
            raise ConfigError(f"task {task.task_id!r} has a vague core contribution")
        if summary == " ".join(task.why_it_matters.lower().split()):
            raise ConfigError(
                f"task {task.task_id!r} uses rationale instead of a concrete core contribution"
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
        if task.status == "BLOCKED_EXTERNAL":
            if len(task.blocker_attempts) < 3:
                raise ConfigError(
                    f"externally blocked task {task.task_id!r} requires at least three attempts"
                )
            attempt_numbers = [attempt.attempt_number for attempt in task.blocker_attempts]
            if attempt_numbers != list(range(1, len(task.blocker_attempts) + 1)):
                raise ConfigError(
                    f"externally blocked task {task.task_id!r} has non-sequential attempts"
                )
            distinct_hypotheses = {attempt.hypothesis for attempt in task.blocker_attempts}
            distinct_actions = {attempt.action_taken for attempt in task.blocker_attempts}
            if len(distinct_hypotheses) < 3 or len(distinct_actions) < 3:
                raise ConfigError(
                    f"externally blocked task {task.task_id!r} attempts are not materially distinct"
                )
            if not task.exact_external_action or not task.exact_resume_condition:
                raise ConfigError(
                    f"externally blocked task {task.task_id!r} requires an exact external action "
                    "and resume condition"
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

    coverage = graph.requirement_coverage
    if coverage is None:
        return
    mapped_ids: set[str] = set()
    mapped_by_task: dict[str, set[str]] = {task_id: set() for task_id in by_id}
    for mapping in coverage.mappings:
        if mapping.requirement_id in mapped_ids:
            raise ConfigError(f"duplicate requirement mapping {mapping.requirement_id!r}")
        if mapping.task_id not in by_id:
            raise ConfigError(
                f"requirement {mapping.requirement_id!r} maps to unknown task {mapping.task_id!r}"
            )
        if mapping.requirement_status == "IMPLEMENTED":
            if mapping.semantic_findings and mapping.disposition != (
                "reopened_semantic_evidence_gap"
            ):
                raise ConfigError(
                    f"implemented requirement {mapping.requirement_id!r} has semantic findings "
                    "but was not reopened"
                )
            if not mapping.semantic_findings and mapping.disposition != "preserved_verified":
                raise ConfigError(
                    f"clean implemented requirement {mapping.requirement_id!r} was not preserved"
                )
        if mapping.requirement_status == "BACKLOG" and mapping.disposition != "excluded_backlog":
            raise ConfigError(f"backlog requirement {mapping.requirement_id!r} was made executable")
        if (
            mapping.requirement_status == "DEPRECATED"
            and mapping.disposition != "excluded_deprecated"
        ):
            raise ConfigError(
                f"deprecated requirement {mapping.requirement_id!r} was made executable"
            )
        mapped_ids.add(mapping.requirement_id)
        mapped_by_task[mapping.task_id].add(mapping.requirement_id)

    if len(mapped_ids) != coverage.total_requirement_rows:
        raise ConfigError(
            "requirement coverage total does not match unique mappings: "
            f"{coverage.total_requirement_rows} != {len(mapped_ids)}"
        )
    for task_id, task in by_id.items():
        if set(task.requirement_ids) != mapped_by_task[task_id]:
            raise ConfigError(f"task {task_id!r} requirement_ids disagree with coverage mappings")
