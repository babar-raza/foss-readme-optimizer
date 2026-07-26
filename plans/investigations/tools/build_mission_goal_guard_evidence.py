"""Build current, reproducible mission-goal and portfolio-scoreboard evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.registry.loader import load_products
from readme_agent.state.git_backend import default_state_backend
from readme_agent.supervisor.mission_control import (
    evaluate_mission,
    mission_state_key,
)
from readme_agent.supervisor.mission_goal_guard import (
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph

REPO_ROOT = Path(__file__).resolve().parents[3]
GRAPH_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
EVIDENCE_DIR = REPO_ROOT / "plans" / "investigations" / "evidence" / "level8-mission-goal-guard"


def _runs_comparison(scoreboard_hash: str) -> dict:
    runs_root = REPO_ROOT / "runs" / "readme-poc"
    manifests = sorted(runs_root.glob("*/**/manifest.json")) if runs_root.is_dir() else []
    summary_path = runs_root / "portfolio-summary.json"
    summary = (
        json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else None
    )
    return {
        "schema_version": 1,
        "durable_scoreboard_sha256": scoreboard_hash,
        "runtime_repository_directory_count": len(
            [path for path in runs_root.iterdir() if path.is_dir()]
        )
        if runs_root.is_dir()
        else 0,
        "runtime_manifest_count": len(manifests),
        "current_portfolio_summary": (
            {
                "path": summary_path.relative_to(REPO_ROOT).as_posix(),
                "registry_path": summary.get("registry_path"),
                "registry_count": summary.get("registry_count"),
                "target_lifecycle_stage": summary.get("target_lifecycle_stage"),
                "result_count": len(summary.get("results", [])),
                "authority_disposition": (
                    "supporting execution slice only; durable per-repository state is authoritative"
                ),
            }
            if summary is not None
            else None
        ),
    }


def main() -> None:
    graph, graph_hash = load_mission_graph(GRAPH_PATH)
    backend = default_state_backend()
    record = backend.load(mission_state_key(graph.mission_authority.mission_id))
    if record is None or record.mission_execution is None:
        raise SystemExit("durable mission state is missing")
    scoreboard = derive_lifecycle_scoreboard(backend)
    evaluation = evaluate_mission(
        graph,
        record.mission_execution.model_copy(update={"lifecycle_scoreboard": scoreboard}),
    )
    scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
    registry_count = len(load_products())
    if scoreboard.denominator != registry_count:
        raise SystemExit("scoreboard denominator disagrees with the current registry")

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_json(EVIDENCE_DIR / "durable-lifecycle-scoreboard.json", scoreboard)
    write_redacted_json(
        EVIDENCE_DIR / "goal-binding-inventory.json",
        {
            "schema_version": 1,
            "graph_path": GRAPH_PATH.relative_to(REPO_ROOT).as_posix(),
            "graph_sha256": graph_hash,
            "core_goal_id": graph.mission_authority.core_goal_id,
            "task_count": len(graph.taskcards),
            "bindings": [
                {
                    "task_id": task.task_id,
                    "status": record.mission_execution.task_statuses.get(task.task_id, task.status),
                    "goal_ids": task.goal_ids,
                    "core_contribution": task.core_contribution.model_dump(mode="json"),
                }
                for task in graph.taskcards
            ],
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "mission-state-projection.json",
        {
            "schema_version": 1,
            "mission_id": evaluation.mission_id,
            "state_version": record.state_version,
            "graph_sha256": record.mission_execution.graph_sha256,
            "graph_drift": record.mission_execution.graph_sha256 != graph_hash,
            "active_task": record.mission_execution.active_task_id,
            "next_task": evaluation.next_task.model_dump(mode="json")
            if evaluation.next_task
            else None,
            "core_goal_active": evaluation.core_goal_active,
            "unresolved_task_count": len(evaluation.unresolved_task_ids),
            "blocked_external_task_count": len(evaluation.blocked_external_task_ids),
            "scoreboard_sha256": scoreboard_hash,
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "runtime-artifact-comparison.json",
        _runs_comparison(scoreboard_hash),
    )
    graph_bytes = GRAPH_PATH.read_bytes()
    write_redacted_json(
        EVIDENCE_DIR / "reproduction.json",
        {
            "schema_version": 1,
            "graph_file_sha256": hashlib.sha256(graph_bytes).hexdigest(),
            "commands": [
                ".venv/Scripts/python -m pytest -q tests/unit/test_mission_control.py "
                "tests/unit/test_git_state_backend_fetch.py tests/unit/test_state_schema.py "
                "tests/unit/test_portfolio.py",
                ".venv/Scripts/python -m ruff check .",
                ".venv/Scripts/python -m ruff format --check .",
                ".venv/Scripts/python -m mypy src",
                ".venv/Scripts/python "
                "scripts/governance/build_level8_requirement_taskcard_coverage.py --check",
                ".venv/Scripts/readme-agent supervise --mission-task-graph "
                "plans/investigations/control/level8-autonomous-mission-task-graph.yaml "
                "--mission-action status --mission-observer Codex",
            ],
        },
    )
    refresh_sha256sums(EVIDENCE_DIR)
    print(f"wrote mission-goal evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
