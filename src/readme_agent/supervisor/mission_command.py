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
    mission_state_key,
    persist_evaluation,
    transition_task,
)
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
    print(f"mission_complete: {str(evaluation.mission_complete).lower()}")
    return 0
