"""CLI-facing adapter for the supervisor's central mission controller."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast

from readme_agent.state.git_backend import default_state_backend
from readme_agent.state.schema import MissionTaskStatus
from readme_agent.supervisor.mission_control import (
    claim_next_task,
    evaluate_mission,
    has_graph_drift,
    mission_state_key,
    persist_evaluation,
    transition_task,
)
from readme_agent.supervisor.mission_goal_guard import derive_lifecycle_scoreboard
from readme_agent.supervisor.mission_graph import load_mission_graph


def run_mission_command(args: argparse.Namespace) -> int:
    graph, graph_sha256 = load_mission_graph(Path(args.mission_task_graph))
    backend = default_state_backend()
    action = args.mission_action

    if action in {"status", "evaluate"}:
        record = (
            persist_evaluation(backend, graph, graph_sha256)
            if action == "evaluate"
            else backend.load(mission_state_key(graph.mission_authority.mission_id))
        )
        if record is None or record.mission_execution is None:
            print("mission state has not been initialized; run --mission-action evaluate")
            return 1
    elif action == "claim":
        record = claim_next_task(
            backend,
            graph,
            graph_sha256,
            claimed_by=args.mission_observer,
        )
    else:
        if not args.mission_task_id or not args.mission_to_status or not args.mission_reason:
            print(
                "error: mission transition requires --mission-task-id, --mission-to-status, "
                "and --mission-reason",
                file=sys.stderr,
            )
            return 2
        record = transition_task(
            backend,
            graph,
            graph_sha256,
            task_id=args.mission_task_id,
            to_status=cast(MissionTaskStatus, args.mission_to_status),
            observed_by=args.mission_observer,
            reason=args.mission_reason,
            evidence_refs=args.mission_evidence,
        )

    state = record.mission_execution
    assert state is not None
    if action == "status":
        state = state.model_copy(
            update={"lifecycle_scoreboard": derive_lifecycle_scoreboard(backend)}
        )
    evaluation = evaluate_mission(graph, state)
    print(f"mission: {evaluation.mission_id}")
    print(f"state_version: {record.state_version}")
    print(f"graph_sha256: {state.graph_sha256}")
    print(f"active_task: {state.active_task_id or '-'}")
    print(
        "eligible_tasks: " + (", ".join(task.task_id for task in evaluation.eligible_tasks) or "-")
    )
    print(f"unresolved_tasks: {len(evaluation.unresolved_task_ids)}")
    print(f"blocked_external_tasks: {len(evaluation.blocked_external_task_ids)}")
    scoreboard = evaluation.lifecycle_scoreboard
    if scoreboard is not None:
        print(f"portfolio_denominator: {scoreboard.denominator}")
        print(f"facts_ready: {scoreboard.facts_ready}/{scoreboard.denominator}")
        print(f"candidate_generated: {scoreboard.candidate_generated}/{scoreboard.denominator}")
        print(
            "deterministic_validated: "
            f"{scoreboard.deterministic_validated}/{scoreboard.denominator}"
        )
        print(f"agent_approved: {scoreboard.agent_approved}/{scoreboard.denominator}")
        print(f"no_op_proven: {scoreboard.no_op_proven}/{scoreboard.denominator}")
        print(f"human_accepted: {scoreboard.human_accepted}/{scoreboard.denominator}")
        print(f"first_failing_boundary: {scoreboard.first_failing_boundary}")
    print(f"core_goal_active: {str(evaluation.core_goal_active).lower()}")
    print(f"active_goal: {evaluation.active_goal_id or '-'}")
    print("concurrent_goals: " + (", ".join(evaluation.concurrent_goal_ids) or "-"))
    print(
        "goal_capacity: "
        + (
            ", ".join(
                f"{name}={value}" for name, value in sorted(evaluation.capacity_allocation.items())
            )
            or "-"
        )
    )
    if evaluation.next_task is None:
        print("next_task: -")
        print("next_task_goals: -")
        print("next_task_contribution: -")
    else:
        print(f"next_task: {evaluation.next_task.task_id}")
        print(f"next_task_stage_goal: {evaluation.next_task.stage_goal_id}")
        print(f"next_task_goals: {', '.join(evaluation.next_task.goal_ids)}")
        print(
            "next_task_contribution: "
            f"{evaluation.next_task.core_contribution.kind}: "
            f"{evaluation.next_task.core_contribution.summary}"
        )
    drifted = has_graph_drift(state, graph_sha256)
    print(f"graph_drift: {str(drifted).lower()}")
    print(f"mission_complete: {str(evaluation.mission_complete).lower()}")
    if action == "status" and drifted:
        print(
            "error: durable mission state is stale against the loaded task graph", file=sys.stderr
        )
        return 1
    return 0
