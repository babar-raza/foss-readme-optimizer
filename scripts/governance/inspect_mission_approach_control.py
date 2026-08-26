"""Read-only report of why the mission controller admits or refuses a task claim.

`supervise --mission-action claim` reports only that nothing was claimable, not
which gate refused. When the approach budget is exhausted or the anti-stall
watermark has lapsed, recovering requires the durable `proposed_fingerprints`
value for the task -- which is not the raw taskcard hash once any replan has
landed. This prints both, plus the attempt ledger the admission decision reads,
so a replan can be authored against real durable state instead of a guess.

Never mutates state: it loads the same backend the controller uses and only reads.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from readme_agent.state.git_backend import default_state_backend
from readme_agent.state.local_poc_backend import default_local_poc_state_backend
from readme_agent.state.mission_routing_backend import MissionRoutingBackend
from readme_agent.supervisor.approach_control import (
    decide_approach_admission,
    proposed_fingerprint,
    task_approach_fingerprint,
)
from readme_agent.supervisor.mission_control import mission_state_key
from readme_agent.supervisor.mission_graph import load_mission_graph

DEFAULT_GRAPH = Path("plans/investigations/control/level8-autonomous-mission-task-graph.yaml")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mission-task-graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument(
        "--task-id",
        action="append",
        default=None,
        help="Report only these task ids (repeatable); default reports every non-admitted task.",
    )
    args = parser.parse_args()

    graph, _graph_sha256 = load_mission_graph(args.mission_task_graph)
    backend = MissionRoutingBackend(default_state_backend(), default_local_poc_state_backend())
    record = backend.load(mission_state_key(graph.mission_authority.mission_id))
    if record is None or record.mission_execution is None:
        print("mission state has not been initialized")
        return 1
    state = record.mission_execution

    print(f"state_version: {record.state_version}")
    print(f"active_task_id: {state.active_task_id}")
    print(f"claimed_by: {state.claimed_by}")
    print(f"claim_expires_at: {state.claim_expires_at}")
    print("")

    selected = set(args.task_id) if args.task_id else None
    for task in graph.taskcards:
        if selected is not None and task.task_id not in selected:
            continue
        decision = decide_approach_admission(state.approach_control, task)
        if selected is None and decision.admitted:
            continue
        print(f"task: {task.task_id}")
        print(f"  status: {state.task_statuses.get(task.task_id, task.status)}")
        print(f"  admitted: {decision.admitted}")
        print(f"  reason: {decision.reason}")
        print(f"  ineffective_attempts: {decision.equivalent_ineffective_attempts}")
        print(f"  requires_replan: {decision.requires_first_principles_replan}")
        durable = proposed_fingerprint(state.approach_control, task)
        print(f"  durable_proposed_fingerprint: {durable}")
        print(f"  raw_taskcard_fingerprint: {task_approach_fingerprint(task)}")
        attempts = [
            attempt
            for attempt in state.approach_control.attempts
            if attempt.task_id == task.task_id
        ]
        for attempt in attempts[-6:]:
            print(
                f"  attempt: outcome={attempt.outcome} started={attempt.started_at} "
                f"narrowed={attempt.last_material_narrowing_at} "
                f"fingerprint={attempt.fingerprint[:12]}"
            )
        print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
