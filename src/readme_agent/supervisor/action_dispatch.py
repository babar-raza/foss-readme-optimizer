"""Dispatch supervisor tasks through permission, effect, and repair gates."""

import json

from readme_agent.capabilities import registry
from readme_agent.capabilities.effect_ledger import dispatch_gated_effect
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.llm.planner_client import PlannerClient
from readme_agent.registry.loader import find_entry
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle import current_lifecycle_recorder
from readme_agent.supervisor import repair
from readme_agent.supervisor.models import DecisionSummary
from readme_agent.supervisor.task import Task, TaskGraph

READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}


def dispatch_and_record(
    graph: TaskGraph,
    task: Task,
    *,
    backend: StateBackend | None,
    org_repo: str,
    decisions: list[DecisionSummary],
    turn: int,
    depth: int = 0,
    extra_kwargs: dict | None = None,
    repair_planner_client: PlannerClient | None = None,
    tools: list[dict] | None = None,
    allowed_permission_classes: set[PermissionClass] | None = None,
) -> Task:
    """Dispatch one task and record a bounded deterministic or planned repair."""

    graph.mark(task.task_id, "EXECUTING")
    tool_call = {"function": {"name": task.capability_id, "arguments": json.dumps(task.arguments)}}
    manifest = registry.get(task.capability_id) if task.capability_id else None
    write_capable = manifest is not None and manifest.side_effect_class in (
        "local_write",
        "remote_write",
    )

    if write_capable:
        write_entry = find_entry(org_repo)
        if write_entry is None or write_entry.mode != "full":
            mode = write_entry.mode if write_entry else "unlisted"
            return graph.mark(
                task.task_id,
                "BLOCKED",
                blocked_reason=(
                    f"{task.capability_id!r} is write-capable but {org_repo} has "
                    f"mode={mode!r}, not 'full' -- refusing to dispatch"
                ),
            )

    effective_write_permissions = allowed_permission_classes or (
        READ_ONLY_PERMISSIONS | {"local_write", "remote_write"}
    )
    if backend is not None and write_capable:
        gated = dispatch_gated_effect(tool_call, effective_write_permissions, backend, org_repo)
        if gated.outcome == "already_applied":
            return graph.mark(task.task_id, "PASSED", result=gated.cached_result)
        if gated.outcome == "blocked_pending_reconciliation":
            return graph.mark(task.task_id, "BLOCKED", blocked_reason=gated.outcome)
        dispatch = gated.dispatch
    else:
        from readme_agent.capabilities.dispatcher import dispatch_tool_call

        dispatch = dispatch_tool_call(
            tool_call, READ_ONLY_PERMISSIONS, extra_kwargs=extra_kwargs, state_backend=backend
        )

    assert dispatch is not None
    if dispatch.outcome == "executed":
        return graph.mark(task.task_id, "PASSED", result=dispatch.result)

    classification = repair.classify_failure(dispatch)
    if dispatch.outcome == "rejected_unknown_capability":
        return graph.mark(task.task_id, "BLOCKED", blocked_reason=classification, gap=dispatch.gap)

    if depth < repair.MAX_REPAIR_ATTEMPTS:
        repair_task = repair.create_repair_task(graph, task, classification, manifest)
        repair_kind = "repair"
        if repair_task is None and repair_planner_client is not None and tools is not None:
            repair_task = repair.select_repair_alternative(
                graph,
                task,
                classification,
                dispatch.error or classification,
                tools,
                repair_planner_client,
            )
            repair_kind = "repair_alternative_selected"
        if repair_task is not None:
            recorder = current_lifecycle_recorder()
            if recorder is not None:
                recorder.checkpoint(
                    "repair_plan",
                    task_id=task.task_id,
                    action=repair_task.capability_id,
                    inputs={
                        "failed_capability": task.capability_id,
                        "classification": classification,
                    },
                    outputs={
                        "repair_task_id": repair_task.task_id,
                        "repair_kind": repair_kind,
                    },
                )
            graph.mark(task.task_id, "FAILED", blocked_reason=dispatch.error)
            detail = (
                f"{task.capability_id!r} failed ({classification}); retrying once"
                if repair_kind == "repair"
                else (
                    f"{task.capability_id!r} failed ({classification}); repair planner "
                    f"selected {repair_task.capability_id!r}"
                )
            )
            decisions.append(DecisionSummary(turn=turn, kind=repair_kind, detail=detail))
            return dispatch_and_record(
                graph,
                repair_task,
                backend=backend,
                org_repo=org_repo,
                decisions=decisions,
                turn=turn,
                depth=depth + 1,
                extra_kwargs=extra_kwargs,
                repair_planner_client=repair_planner_client,
                tools=tools,
                allowed_permission_classes=allowed_permission_classes,
            )
        if repair_planner_client is not None:
            decisions.append(
                DecisionSummary(
                    turn=turn,
                    kind="repair_escalated",
                    detail=(
                        f"{task.capability_id!r} failed ({classification}); no repair "
                        "alternative found -- escalating"
                    ),
                )
            )

    return graph.mark(task.task_id, "BLOCKED", blocked_reason=dispatch.error or classification)
