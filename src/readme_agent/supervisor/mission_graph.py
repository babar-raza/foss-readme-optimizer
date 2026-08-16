"""Load and validate the supervisor's declarative central mission graph."""

import hashlib
from pathlib import Path

import yaml

from readme_agent.errors import ConfigError
from readme_agent.state.mission_goal_schema import ExecutionCampaignId, StageGoalId
from readme_agent.supervisor.mission_schema import (
    DeferredTaskRecordV1,
    MissionTaskGraphV1,
    RequirementCatalogRecordV1,
    TaskCardV1,
)

_SUBORDINATE_GOAL_IDS = {
    "GOAL-TRUTH",
    "GOAL-README",
    "GOAL-PROFILE",
    "GOAL-AUTONOMY",
    "GOAL-DELIVERY",
    "GOAL-MATURITY",
}
_STAGE_GOAL_ORDERS = {
    "GOAL-P0-PLAN-FREEZE": 0,
    "GOAL-V0A-FIRST-VERIFIED-README": 5,
    "GOAL-T0-TRUSTED-QUALIFICATION": 10,
    "GOAL-V0-VERIFIED-PYTHON-POC": 11,
    "GOAL-TP-TRUSTED-COHORT-POC": 12,
    "GOAL-T0R-TRUSTED-ADVERSARIAL-QUALIFICATION": 13,
    "GOAL-V0B-POST-PYTHON-SLICES": 14,
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
_HISTORICAL_TRUSTED_STAGE_GOALS: set[StageGoalId] = {
    "GOAL-T0-TRUSTED-QUALIFICATION",
    "GOAL-TP-TRUSTED-COHORT-POC",
    "GOAL-T0R-TRUSTED-ADVERSARIAL-QUALIFICATION",
    "GOAL-T1-TRUSTED-PORTFOLIO",
    "GOAL-T2-WORKFLOW-STAGING",
    "GOAL-T3-HOSTED-TRUSTED-DELIVERY",
}
_CAMPAIGN_ORDERS: dict[ExecutionCampaignId, int] = {
    "CAMP-PLAN-FREEZE": 0,
    "CAMP-SHARED-ACCELERATION": 10,
    "CAMP-FIRST-PYTHON-SLICE": 20,
    "CAMP-PYTHON-PORTFOLIO": 30,
    "CAMP-THREE-SLICES": 40,
    "CAMP-GATE-A-PORTFOLIO": 50,
    "CAMP-GATE-B-AND-LATER": 60,
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
    _validate_graph(graph, graph_path=path)
    return graph, hashlib.sha256(payload).hexdigest()


def _resolve_reference(graph_path: Path, reference_path: str) -> Path:
    candidates = [Path.cwd(), *graph_path.resolve().parents]
    for root in candidates:
        candidate = root / reference_path
        if candidate.is_file():
            return candidate
    raise ConfigError(f"mission catalog reference does not exist: {reference_path}")


def _validate_reference(graph_path: Path, reference, label: str) -> Path:
    path = _resolve_reference(graph_path, reference.path)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != reference.sha256:
        raise ConfigError(
            f"{label} hash mismatch for {reference.path}: {actual} != {reference.sha256}"
        )
    return path


def _validate_graph(graph: MissionTaskGraphV1, *, graph_path: Path) -> None:
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
    by_goal = {goal.goal_id: goal for goal in stage_goals}
    for goal_id in _HISTORICAL_TRUSTED_STAGE_GOALS:
        goal = by_goal[goal_id]
        if goal.execution_required or goal.product_effects_allowed or goal.reserved_trusted_lanes:
            raise ConfigError(
                f"historical trusted goal {goal_id!r} must be non-executable with zero "
                "effect and reserved capacity"
            )

    campaigns = graph.campaign_catalog
    if {campaign.campaign_id: campaign.order for campaign in campaigns} != _CAMPAIGN_ORDERS:
        raise ConfigError("mission campaign_catalog does not match the governed seven campaigns")

    requirement_catalog = _validate_reference(
        graph_path, graph.requirement_catalog, "requirement catalog"
    )
    coverage_path = _validate_reference(
        graph_path, graph.requirement_coverage, "requirement coverage"
    )
    deferred_catalog = _validate_reference(
        graph_path, graph.deferred_task_catalog, "deferred task catalog"
    )
    requirement_lines = [
        line for line in requirement_catalog.read_text(encoding="utf-8").splitlines() if line
    ]
    if len(requirement_lines) != graph.requirement_catalog.record_count:
        raise ConfigError("requirement catalog record count does not match its graph reference")
    requirement_records = []
    for lineno, line in enumerate(requirement_lines, start=1):
        try:
            requirement_records.append(RequirementCatalogRecordV1.model_validate_json(line))
        except ValueError as exc:
            raise ConfigError(
                f"invalid requirement catalog record at line {lineno}: {exc}"
            ) from exc
    requirement_ids = [record.requirement_id for record in requirement_records]
    if len(requirement_ids) != len(set(requirement_ids)):
        raise ConfigError("requirement catalog contains duplicate stable IDs")
    if sum(1 for line in coverage_path.read_text(encoding="utf-8").splitlines() if line) < 1:
        raise ConfigError("requirement coverage artifact is empty")
    deferred_lines = [
        line for line in deferred_catalog.read_text(encoding="utf-8").splitlines() if line
    ]
    if len(deferred_lines) != graph.deferred_task_catalog.record_count:
        raise ConfigError("deferred task catalog record count does not match its graph reference")
    if len(graph.taskcards) > 15:
        raise ConfigError("active mission graph exceeds the fifteen-task authority budget")

    deferred_records: list[tuple[DeferredTaskRecordV1, str]] = []
    for lineno, line in enumerate(deferred_lines, start=1):
        try:
            deferred_records.append(
                (
                    DeferredTaskRecordV1.model_validate_json(line),
                    hashlib.sha256(line.encode()).hexdigest(),
                )
            )
        except ValueError as exc:
            raise ConfigError(
                f"invalid deferred task catalog record at line {lineno}: {exc}"
            ) from exc
    deferred_by_id = {task.task_id: task for task in graph.deferred_task_index}
    if len(deferred_by_id) != len(graph.deferred_task_index):
        raise ConfigError("deferred task index contains duplicate IDs")
    if set(deferred_by_id) & {task.task_id for task in graph.taskcards}:
        raise ConfigError("active and deferred mission task IDs overlap")
    if len(deferred_by_id) != graph.deferred_task_catalog.record_count:
        raise ConfigError("deferred task index does not cover the deferred task catalog")
    record_by_id = {
        record.task.task_id: (record, line_hash) for record, line_hash in deferred_records
    }
    if len(record_by_id) != len(deferred_records):
        raise ConfigError("deferred task catalog contains duplicate stable IDs")
    if set(record_by_id) != set(deferred_by_id):
        raise ConfigError("deferred task index IDs do not match the catalog")
    known_task_ids = set(record_by_id) | {task.task_id for task in graph.taskcards}
    for task_id, index in deferred_by_id.items():
        record, line_hash = record_by_id[task_id]
        if record.task.mission_id != authority.mission_id:
            raise ConfigError(
                f"deferred task {task_id!r} belongs to {record.task.mission_id!r}, "
                f"not mission {authority.mission_id!r}"
            )
        missing_dependencies = set(record.task.dependencies) - known_task_ids
        if missing_dependencies:
            raise ConfigError(
                f"deferred task {task_id!r} has unknown dependencies {sorted(missing_dependencies)}"
            )
        if record.task.parent_task_id not in {*known_task_ids, None}:
            raise ConfigError(
                f"deferred task {task_id!r} has unknown parent_task_id "
                f"{record.task.parent_task_id!r}"
            )
        expected_status = (
            "DEFERRED_WITH_REASON"
            if record.activation_group == "historical-control"
            else record.task.status
        )
        if (
            index.record_sha256 != line_hash
            or index.stage_goal_id != record.task.stage_goal_id
            or index.activation_group != record.activation_group
            or index.status != expected_status
        ):
            raise ConfigError(f"deferred task index metadata mismatch for {task_id!r}")

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
        historical = task.stage_goal_id in _HISTORICAL_TRUSTED_STAGE_GOALS
        if historical and task.campaign_id is not None:
            raise ConfigError(
                f"historical task {task.task_id!r} cannot join an executable campaign"
            )
        if not historical and task.campaign_id is None:
            raise ConfigError(f"executable task {task.task_id!r} must belong to one campaign")
        if (
            task.concurrency_class == "read_only_assurance_isolated"
            and not stage_goal.concurrent_when_earlier_primary
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
        if task.core_contribution.kind == "visible_deliverable" and task.execution_focus is None:
            raise ConfigError(
                f"visible-deliverable task {task.task_id!r} requires one execution_focus"
            )
        by_id[task.task_id] = task

    for task in graph.taskcards:
        missing = [
            dependency
            for dependency in task.dependencies
            if dependency not in by_id and dependency not in deferred_by_id
        ]
        if missing:
            raise ConfigError(f"task {task.task_id!r} has unknown dependencies {missing}")
        if (
            task.parent_task_id is not None
            and task.parent_task_id not in by_id
            and task.parent_task_id not in deferred_by_id
        ):
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
        if task_id not in by_id:
            # A deferred (retired) task cannot depend on an active one, so it
            # can never be part of an active-graph cycle; treat it as a leaf.
            return
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

    if any(len(task.requirement_ids) > 25 for task in graph.taskcards):
        raise ConfigError("an active task exceeds the twenty-five-requirement context budget")
