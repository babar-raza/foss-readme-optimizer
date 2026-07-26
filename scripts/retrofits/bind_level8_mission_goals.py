"""Add explicit goal and core-contribution bindings to the Level-8 task graph."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

GRAPH_PATH = Path("plans/investigations/control/level8-autonomous-mission-task-graph.yaml")

_LANE_GOALS: dict[str, tuple[str, ...]] = {
    "actions-runtime": ("GOAL-AUTONOMY",),
    "baseline-reproduction": ("GOAL-AUTONOMY",),
    "canonical-runtime": ("GOAL-AUTONOMY",),
    "durable-runtime": ("GOAL-AUTONOMY",),
    "facts-and-ownership": ("GOAL-TRUTH",),
    "github-app-integration": ("GOAL-DELIVERY",),
    "governance-truth": ("GOAL-AUTONOMY",),
    "heterogeneous-rollout": ("GOAL-MATURITY",),
    "human-acceptance": ("GOAL-DELIVERY",),
    "java-pilot": ("GOAL-DELIVERY",),
    "level8-operations": ("GOAL-MATURITY",),
    "local-independent-review": ("GOAL-README",),
    "local-poc-runtime": ("GOAL-AUTONOMY",),
    "local-portfolio-proof": ("GOAL-README",),
    "local-product-truth": ("GOAL-TRUTH",),
    "local-qualification": ("GOAL-README",),
    "local-readme-composition": ("GOAL-README",),
    "mission-control": ("GOAL-AUTONOMY",),
    "preproduction-fidelity": ("GOAL-README", "GOAL-AUTONOMY"),
    "presentation-intelligence": ("GOAL-README", "GOAL-PROFILE"),
    "proposal-effects": ("GOAL-DELIVERY",),
}

_SAFETY_LANES = {
    "actions-runtime",
    "baseline-reproduction",
    "canonical-runtime",
    "durable-runtime",
    "governance-truth",
    "local-poc-runtime",
    "mission-control",
}
_ACCEPTANCE_LANES = {
    "github-app-integration",
    "heterogeneous-rollout",
    "human-acceptance",
    "java-pilot",
    "level8-operations",
    "local-independent-review",
    "local-portfolio-proof",
    "local-qualification",
    "proposal-effects",
}


def _contribution_kind(lane: str) -> str:
    if lane in _SAFETY_LANES:
        return "indispensable_safety"
    if lane in _ACCEPTANCE_LANES:
        return "acceptance_proof"
    return "visible_deliverable"


def main() -> None:
    payload = GRAPH_PATH.read_text(encoding="utf-8")
    raw = yaml.safe_load(payload)
    tasks = {task["task_id"]: task for task in raw["taskcards"]}
    unknown_lanes = sorted({task["lane"] for task in tasks.values()} - _LANE_GOALS.keys())
    if unknown_lanes:
        raise SystemExit(f"refusing migration with unmapped task lanes: {unknown_lanes}")
    already_bound = sorted(task_id for task_id, task in tasks.items() if "goal_ids" in task)
    if already_bound:
        raise SystemExit(f"refusing duplicate goal migration: {already_bound}")

    lines = payload.splitlines()
    output: list[str] = []
    current_task_id: str | None = None
    inserted: set[str] = set()
    for line in lines:
        if line.startswith("- task_id: "):
            current_task_id = line.removeprefix("- task_id: ").strip()
        if line.startswith("  requirement_ids:") and current_task_id is not None:
            task = tasks[current_task_id]
            for goal_id in _LANE_GOALS[task["lane"]]:
                if current_task_id not in inserted:
                    output.append("  goal_ids:")
                output.append(f"  - {goal_id}")
                inserted.add(current_task_id)
            output.extend(
                [
                    "  core_contribution:",
                    f"    kind: {_contribution_kind(task['lane'])}",
                    f"    summary: {json.dumps(task['objective'], ensure_ascii=False)}",
                ]
            )
        output.append(line)

    missing = sorted(set(tasks) - inserted)
    if missing:
        raise SystemExit(f"refusing partial goal migration; unbound tasks: {missing}")
    migrated = "\n".join(output) + "\n"
    temporary = GRAPH_PATH.with_suffix(".yaml.goal-bindings")
    temporary.write_text(migrated, encoding="utf-8", newline="\n")
    temporary.replace(GRAPH_PATH)
    print(f"bound {len(inserted)} taskcards in {GRAPH_PATH}")


if __name__ == "__main__":
    main()
