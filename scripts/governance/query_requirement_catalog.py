"""Load one bounded, graph-mapped requirement slice from the typed catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from readme_agent.errors import ConfigError
from readme_agent.supervisor.mission_graph import load_mission_graph

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)


def load_slice(task_id: str) -> dict:
    graph, graph_sha256 = load_mission_graph(GRAPH_PATH)
    by_id = {task.task_id: task for task in graph.taskcards}
    task = by_id.get(task_id)
    if task is None:
        raise ConfigError(f"task {task_id!r} is not in the active mission horizon")
    if len(task.requirement_ids) > 25:
        raise ConfigError(f"task {task_id!r} exceeds the 25-requirement context budget")
    catalog_path = REPO_ROOT / graph.requirement_catalog.path
    records = [
        json.loads(line) for line in catalog_path.read_text(encoding="utf-8").splitlines() if line
    ]
    records_by_id = {record["requirement_id"]: record for record in records}
    if len(records_by_id) != len(records):
        raise ConfigError("typed requirement catalog contains duplicate IDs")
    missing = set(task.requirement_ids) - set(records_by_id)
    if missing:
        raise ConfigError(f"task {task_id!r} maps missing requirement IDs: {sorted(missing)}")
    return {
        "schema": "TaskRequirementSliceV1",
        "task_id": task_id,
        "graph_sha256": graph_sha256,
        "catalog_sha256": graph.requirement_catalog.sha256,
        "requirement_count": len(task.requirement_ids),
        "requirements": [records_by_id[requirement_id] for requirement_id in task.requirement_ids],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(load_slice(args.task_id), indent=2) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
